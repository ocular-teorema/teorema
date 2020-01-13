import queue
import pika
import os
import sys
import traceback
import threading
import logging
import json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theorema.settings')
import django
django.setup()

from queue_api.status import StatusMessages
from queue_api.storages import StorageListMessage, StorageDeleteMessage, StorageAddMessages, StorageUpdateMessage
from queue_api.cameras import CameraAddMessages, CameraListMessages, CameraSetRecordingMessages, CameraDeleteMessages, CameraUpdateMessages
from queue_api.scheduler import SchedulesAddMessage, ScheduleListMessage, SchedulesDeleteMessage, SchedulesUpdateMessage
from queue_api.common import pika_setup_connection, base_send_in_queue, get_server_name
from queue_api.ptz_control import PanControlMessage, TiltControlMessage, ZoomControlMessage
from queue_api.archive import VideosGetMessage, ArchiveEventsMessage
from queue_api.events import EventsSendMessage
from queue_api.configuration import ConfigExportMessage, ConfigImportMessage, ConfigurationResetMessage
from queue_api.scheduler import CameraScheduler
from queue_api.messages import InvalidMessageStructureError, InvalidMessageTypeError
from queue_api.settings import *


class PikaHandler(threading.Thread):

    def __init__(self):
        super().__init__()

        self.server_name = get_server_name()
        self.response_exchange = 'driver'
        print('server name (exchange): {name}'.format(name=self.server_name), flush=True)
        print('server response exchange: {name}'.format(name=self.response_exchange), flush=True)

        self.scheduler = CameraScheduler()
        self.scheduler.start()
        print('scheduler started', flush=True)

    def run(self):
        print('starting receiver', flush=True)
        connection = pika_setup_connection()
        channel = connection.channel()

        channel.exchange_declare(exchange=self.server_name, exchange_type=RABBITMQ_EXCHANGE_TYPE_OCULAR, durable=False, auto_delete=False)
        result = channel.queue_declare('')

        queue_name = result.method.queue
        channel.queue_bind(exchange=self.server_name, queue=queue_name, routing_key='')

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=self.callback,
            # auto_ack=True
        )

        print('receiver started', flush=True)
        channel.start_consuming()
        self.scheduler.start()


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

    def callback(self, ch, method, properties, body):
        print('received', body, properties, method, flush=True)
        try:
            message = json.loads(body.decode())
            if not self.verify_message(message):
                return
            message_type = message['type']

            getattr(self, message_type, self.unknown_handler)(message)

        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())),
                  flush=True)
        else:
            ch.basic_ack(delivery_tag=method.delivery_tag)

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

    def cameras_ptz_move_horizontal(self, message):
        print('horizontal control request', flush=True)

        cameras_request = PanControlMessage()
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_ptz_move_vertical(self, message):
        print('vertical control request', flush=True)

        cameras_request = TiltControlMessage()
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_ptz_zoom(self, message):
        print('zoom control request', flush=True)

        cameras_request = ZoomControlMessage()
        cameras_request.handle_request(message)
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
    receiver = PikaHandler()
    receiver.start()
