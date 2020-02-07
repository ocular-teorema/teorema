import queue
import pika
import os
import sys
import traceback
import threading
import functools
import time
import logging
import json
import inspect

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theorema.settings')
import django

django.setup()

from theorema.cameras.models import Camera

from queue_api.status import StatusMessages
from queue_api.storages import StorageListMessage, StorageDeleteMessage, StorageAddMessages, StorageUpdateMessage
from queue_api.cameras import CameraAddMessages, CameraListMessages, CameraSetRecordingMessages, CameraDeleteMessages, \
    CameraUpdateMessages
from queue_api.scheduler import SchedulesAddMessage, ScheduleListMessage, SchedulesDeleteMessage, SchedulesUpdateMessage
from queue_api.common import pika_setup_connection, base_send_in_queue, get_server_name
from queue_api.archive import VideosGetMessage, ArchiveEventsMessage
from queue_api.ptz_control import AbsoluteMoveMessage, ContinuousMoveMessage, RelativeMoveMessage, StopMoveMessage, \
    SetHomeMessage, SetPresetMessage, GotoHomeMessage, GotoPresetMessage, GetPresetsMessage
from queue_api.archive import VideosGetMessage
from queue_api.events import EventsSendMessage
from queue_api.configuration import ConfigExportMessage, ConfigImportMessage, ConfigurationResetMessage
from queue_api.scheduler import CameraScheduler
from queue_api.messages import InvalidMessageStructureError, InvalidMessageTypeError
from queue_api.settings import *

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)

INBUILT_CLASS_METHODS = ['__init__', '__repr__', '_bootstrap', '_bootstrap_inner', '_delete', '_reset_internal_locks',
                         '_set_ident', '_set_tstate_lock', '_stop', '_wait_for_tstate_lock', 'getName', 'isAlive',
                         'isDaemon', 'is_alive', 'join', 'reset', 'run', 'setDaemon', 'setName', 'start']


class PikaMaster:

    def __init__(self):
        self.camera_list = self.get_camera_list()
        self.prefetch_count = 4

        print('Total cameras: {}'.format(len(self.camera_list)), flush=True)
        print('Prefetching in async: {}'.format(self.prefetch_count), flush=True)
        print('Number of threads: {}'.format(len(self.camera_list) + self.prefetch_count), flush=True)

    def get_camera_list(self):
        return Camera.objects.values_list('uid', flat=True)

    def start(self):
        for cam in self.camera_list:
            synchronous_thread = PikaThread(cam, False)
            synchronous_thread.run()

        async_thread = PikaThread('common', True, 4)
        async_thread.run()


class PikaThread(threading.Thread):

    def __init__(self, thread_name, async_thread=False, prefetch_count=None):
        super().__init__()

        self.worker_name = thread_name.upper()
        self.server_name = get_server_name()
        self.response_exchange = 'driver'
        print('server name (exchange): {name}'.format(name=self.server_name), flush=True)
        print('server response exchange: {name}'.format(name=self.response_exchange), flush=True)

        self.scheduler = CameraScheduler()
        self.scheduler.start()
        print('scheduler started'.format(self.worker_name), flush=True)

        if async_thread:
            self.async_thread = True
            self.callback = self.asynchronous_callback
            self.prefetch_count = prefetch_count
            self.ptz_cam = thread_name
        else:
            self.async_thread = False
            self.callback = self.synchronous_callback

    def get_all_commands(self):
        members = inspect.getmembers(self, predicate=inspect.ismethod)
        synchronous = []
        asynchronous = []
        for x in members:
            name = x[0]
            if 'cameras_ptz' in name:
                synchronous.append(name)
            else:
                if name not in INBUILT_CLASS_METHODS:
                    asynchronous.append(name)

        return {'synchronous': synchronous, 'asynchronous': asynchronous}

    def run(self):
        print('starting receiver', flush=True)
        connection = pika_setup_connection(heartbeat=5)
        channel = connection.channel()

        channel.exchange_declare(exchange=self.server_name, exchange_type=RABBITMQ_EXCHANGE_TYPE_OCULAR,
                                 passive=False, durable=False, auto_delete=False)

        result = channel.queue_declare(queue='', auto_delete=True)

        queue_name = result.method.queue
        channel.queue_bind(exchange=self.server_name, queue=queue_name, routing_key='')
        if self.async_thread:
            channel.basic_qos(prefetch_count=self.prefetch_count)

            threads = []
            base_callback = functools.partial(self.callback, args=(connection, threads))
        else:
            base_callback = self.callback

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=base_callback
            # on_message_callback=threaded_callback,
        )

        print('{}: receiver started'.format(self.worker_name), flush=True)
        channel.start_consuming()

    def synchronous_callback(self, ch, method, properties, body):
        print('received', body, properties, method, flush=True)
        try:
            message = json.loads(body.decode())
            if not self.verify_message(message):
                return
            message_type = message['type']
            if message_type in self.get_all_commands()['synchronous']:
                getattr(self, message_type, self.unknown_handler)(message)
            else:
                pass

        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
        else:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def asynchronous_callback(self, ch, method_frame, _header_frame, body, args):
        (conn, thrds) = args
        delivery_tag = method_frame.delivery_tag
        print(('threads: ', thrds), flush=True)
        t = threading.Thread(target=self.asynchronous_worker, args=(conn, ch, delivery_tag, body))
        t.start()
        thrds.append(t)

    def asynchronous_worker(self, conn, ch, delivery_tag, body):
        thread_id = threading.get_ident()
        LOGGER.info('Thread id: %s Delivery tag: %s Message body: %s', thread_id,
                    delivery_tag, body)
        try:
            message = json.loads(body.decode())
            if not self.verify_message(message):
                LOGGER.info('3')
                return
            message_type = message['type']
            LOGGER.info(json.loads(body.decode())['type'])
            if message_type in self.get_all_commands()['synchronous']:
                print('Received PTZ control message on cam:', message['camera_id'], flush=True)
                if ('camera_id' in message) and (message['camera_id'] == self.ptz_cam):
                    getattr(self, message_type, self.unknown_handler)(message)
                else:
                    pass
            else:
                pass

        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())),
                  flush=True)

        cb = functools.partial(self.asynchronous_ack_message, ch, delivery_tag)
        conn.add_callback_threadsafe(cb)

    def asynchronous_ack_message(self, ch, delivery_tag):
        if ch.is_open:
            ch.basic_ack(delivery_tag)
        else:
            pass

    def verify_message(self, message):
        if 'uuid' and 'type' not in message:
            valid = False
        elif not isinstance(message['uuid'], str):
            valid = False
        elif not isinstance(message['type'], str):
            valid = False
        else:
            valid = True

        if not valid:
            uuid = message['uuid'] if 'uuid' in message else None
            error = InvalidMessageStructureError(uuid=uuid)
            base_send_in_queue(self.response_exchange, str(error))
            return False
        else:
            return True

    def unknown_handler(self, message):
        print('unknown message', message, flush=True)
        error = InvalidMessageTypeError(message['type'], message['uuid'])
        base_send_in_queue(self.response_exchange, str(error))

    def cameras_add(self, message):
        print('camera add request message received', flush=True)

        camera_message = CameraAddMessages(self.scheduler)
        camera_message.handle_request(message)
        print('message ok', flush=True)

    def cameras_list(self, message):
        print('camera list request message received', flush=True)

        camera_message = CameraListMessages()
        camera_message.handle_request(message)
        print('message ok', flush=True)

    def cameras_update(self, message):
        print('camera update request message received', flush=True)

        camera_message = CameraUpdateMessages(self.scheduler)
        camera_message.handle_request(message)
        print('message ok')

    def status(self, message):
        print('status request message received', flush=True)

        status_request = StatusMessages()
        status_request.handle_request(message)
        print('message ok', flush=True)

    def status_timed(self, message):
        print('status request message received', flush=True)
        print('sleeping 30s', flush=True)
        time.sleep(30)
        print('awooken', flush=True)

        status_request = StatusMessages()
        status_request.handle_request(message)
        print('message ok', flush=True)

    def storages_add(self, message):
        print('storage add request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        storages_request = StorageAddMessages()
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def storages_delete(self, message):
        print('storage delete request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        storages_request = StorageDeleteMessage()
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def storages_list(self, message):
        print('storage get request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        storages_request = StorageListMessage()
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def storages_update(self, message):
        print('storage get request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        storages_request = StorageUpdateMessage()
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_set_recording(self, message):
        print('storage get request', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        cameras_request = CameraSetRecordingMessages()
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_delete(self, message):
        print('cameras delete request', flush=True)

        cameras_request = CameraDeleteMessages(self.scheduler)
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_ptz_absolute_move(self, message):
        print('absolute move request', flush=True)

        move_instance = getattr(self, 'AbsoluteMoveMessage', None)
        if not move_instance:
            cameras_request = AbsoluteMoveMessage()
            self.AbsoluteMoveMessage = cameras_request
            cameras_request.handle_request(message)
        else:
            print('move instance already exist', flush=True)
            move_instance.handle_request(message)

        print('message ok', flush=True)

    def cameras_ptz_continuous_move(self, message):
        print('continuous request', flush=True)

        move_instance = getattr(self, 'ContinuousMoveMessage', None)
        if not move_instance:
            cameras_request = ContinuousMoveMessage()
            self.ContinuousMoveMessage = cameras_request
            cameras_request.handle_request(message)
        else:
            print('move instance already exist', flush=True)
            move_instance.handle_request(message)

        print('message ok', flush=True)

    def cameras_ptz_relative_move(self, message):
        print('relative move request', flush=True)

        move_instance = getattr(self, 'RelativeMoveMessage', None)
        if not move_instance:
            cameras_request = RelativeMoveMessage()
            self.RelativeMoveMessage = cameras_request
            cameras_request.handle_request(message)
        else:
            print('move instance already exist', flush=True)
            move_instance.handle_request(message)

        print('message ok', flush=True)

    def cameras_ptz_stop_move(self, message):
        print('stop move request', flush=True)

        move_instance = getattr(self, 'StopMoveMessage', None)
        if not move_instance:
            cameras_request = StopMoveMessage()
            self.StopMoveMessage = cameras_request
            cameras_request.handle_request(message)
        else:
            print('move instance already exist', flush=True)
            move_instance.handle_request(message)

        print('message ok', flush=True)

    def cameras_ptz_set_home(self, message):
        print('set home request', flush=True)

        move_instance = getattr(self, 'SetHomeMessage', None)
        if not move_instance:
            cameras_request = SetHomeMessage()
            self.SetHomeMessage = cameras_request
            cameras_request.handle_request(message)
        else:
            print('move instance already exist', flush=True)
            move_instance.handle_request(message)

        print('message ok', flush=True)

    def cameras_ptz_set_preset(self, message):
        print('set preset request', flush=True)

        move_instance = getattr(self, 'SetPresetMessage', None)
        if not move_instance:
            cameras_request = SetPresetMessage()
            self.SetPresetMessage = cameras_request
            cameras_request.handle_request(message)
        else:
            print('move instance already exist', flush=True)
            move_instance.handle_request(message)

        print('message ok', flush=True)

    def cameras_ptz_goto_home(self, message):
        print('goto home request', flush=True)

        move_instance = getattr(self, 'GotoHomeMessage', None)
        if not move_instance:
            cameras_request = GotoHomeMessage()
            self.GotoHomeMessage = cameras_request
            cameras_request.handle_request(message)
        else:
            print('move instance already exist', flush=True)
            move_instance.handle_request(message)

        print('message ok', flush=True)

    def cameras_ptz_goto_preset(self, message):
        print('goto preset request', flush=True)

        move_instance = getattr(self, 'GotoPresetMessage', None)
        if not move_instance:
            cameras_request = GotoPresetMessage()
            self.GotoPresetMessage = cameras_request
            cameras_request.handle_request(message)
        else:
            print('move instance already exist', flush=True)
            move_instance.handle_request(message)

        print('message ok', flush=True)

    def cameras_ptz_get_presets(self, message):
        print('get presets request', flush=True)

        move_instance = getattr(self, 'GetPresetsMessage', None)
        if not move_instance:
            cameras_request = GetPresetsMessage()
            self.GetPresetsMessage = cameras_request
            cameras_request.handle_request(message)
        else:
            print('move instance already exist', flush=True)
            move_instance.handle_request(message)

        print('message ok', flush=True)

    def archive_video(self, message):
        print('archive video request', flush=True)

        cameras_request = VideosGetMessage()
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def archive_events(self, message):
        print('archive video request', flush=True)

        cameras_request = ArchiveEventsMessage()
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_event(self, message):
        print('cameras event request', flush=True)

        cameras_request = EventsSendMessage()
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def config_export(self, message):
        print('config export request, flush=True')

        config_export_msg = ConfigExportMessage()
        config_export_msg.handle_request(message)
        print('message ok', flush=True)

    def config_import(self, message):
        print('config export request, flush=True')

        config_export_msg = ConfigImportMessage(self.scheduler)
        config_export_msg.handle_request(message)
        print('message ok', flush=True)

    def reset(self, message):
        print('reset message request', flush=True)

        reset_msg = ConfigurationResetMessage(self.scheduler)
        reset_msg.handle_request(message)
        print('message ok', flush=True)

    def schedules_add(self, message):
        print('schedule add request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        schedules_request = SchedulesAddMessage()
        schedules_request.handle_request(message)
        print('message ok', flush=True)

    def schedules_delete(self, message):
        print('schedule delete request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        schedules_request = SchedulesDeleteMessage()
        schedules_request.handle_request(message)
        print('message ok', flush=True)

    def schedules_list(self, message):
        print('schedule get request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        schedules_request = ScheduleListMessage()
        schedules_request.handle_request(message)
        print('message ok', flush=True)

    def schedules_update(self, message):
        print('schedule get request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        schedules_request = SchedulesUpdateMessage()
        schedules_request.handle_request(message)
        print('message ok', flush=True)


if __name__ == '__main__':
    logging.getLogger('pika').setLevel(logging.WARNING)
    handler = PikaMaster()
    handler.start()
