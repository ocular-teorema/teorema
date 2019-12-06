import queue
import pika
import os
import sys
import traceback
import threading
import json
import uuid
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theorema.settings')
import django
django.setup()

from theorema.cameras.models import Camera, Storage

from queue_api.status import StatusMessages
from queue_api.storages import StorageListMessage, StorageDeleteMessage, StorageAddMessages, StorageUpdateMessage
from queue_api.cameras import CameraAddMessages, CameraListMessages, CameraSetRecordingMessages, CameraDeleteMessages, CameraUpdateMessages
from queue_api.common import pika_setup_connection, exchange_from_server_name
from queue_api.ptz_control import PanControlMessage, TiltControlMessage, ZoomControlMessage
from queue_api.archive import VideosGetMessage
from queue_api.events import EventsSendMessage


class SelfPublished(Exception):
    pass


class InvalidTopic(Exception):
    pass


class PikaHandler(threading.Thread):

    def __init__(self):
        super().__init__()

        self.server_name = uuid.getnode()
        print('server name: {name}'.format(name=self.server_name), flush=True)

        self.server_exchange = exchange_from_server_name(self.server_name)
        print('exchange:', self.server_exchange, flush=True)

#        self.is_object_exchange = False
#        self.object_exchange_id = None
#        self.object_exchange_type = None

#    def set_object_exchange(self, object_type, object_id):
#
#        if object_type == 'camera':
#            self.server_exchange = exchange_with_camera_name(self.server_exchange, object_id)
#        elif object_type == 'storage':
#            self.server_exchange = exchange_with_storage_name(self.server_exchange, object_id)
#
#        self.is_object_exchange = True
#        self.object_exchange_id = object_id
#        self.object_exchange_type = object_type
#
#        print('set object topic:', self.server_exchange, flush=True)

    def run(self):
        print('starting receiver', flush=True)
        connection = pika_setup_connection()
        channel = connection.channel()

        channel.exchange_declare(exchange=self.server_exchange, exchange_type='topic')
        result = channel.queue_declare('', exclusive=True)

        queue_name = result.method.queue
        channel.queue_bind(exchange=self.server_exchange, queue=queue_name, routing_key='')

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=self.callback,
            # auto_ack=True
        )

        print('receiver started', flush=True)
        channel.start_consuming()

    def callback(self, ch, method, properties, body):
        print('received', body, properties, method, flush=True)
        try:
            # if not properties.app_id or int(properties.app_id) != self.server_name:
            #if properties.app_id and properties.app_id == str(self.server_name):
            #    print('message published by self, skipping', flush=True)
            #    raise SelfPublished

            #else:
            message = json.loads(body.decode())
            message_type = message['type']

            getattr(self, message_type, self.unknown_handler)(message)


        except SelfPublished:
            pass
        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())),
                  flush=True)
        else:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def unknown_handler(self, message):
        print('unknown message', message, flush=True)

    def cameras_add(self, message):
        print('camera add request message received', flush=True)

        camera_message = CameraAddMessages(self.server_exchange, self.server_name)
        camera_message.handle_request(message)
        print('message ok', flush=True)

    def cameras_list(self, message):
        print('camera list request message received', flush=True)

        camera_message = CameraListMessages(self.server_exchange, self.server_name)
        camera_message.handle_request(message)
        print('message ok', flush=True)

    def cameras_update(self, message):
        print('camera update request message received', flush=True)

        camera_message = CameraUpdateMessages(self.server_exchange, self.server_name)
        camera_message.handle_request(message)
        print('message ok')

    def status(self, message):
        print('status request message received', flush=True)

        status_request = StatusMessages(self.server_exchange, self.server_name)
        status_request.handle_request(message)
        print('message ok', flush=True)

    def storages_add(self, message):
        print('storage add request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        storages_request = StorageAddMessages(self.server_exchange, self.server_name)
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def storages_delete(self, message):
        print('storage delete request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        storages_request = StorageDeleteMessage(self.server_exchange, self.server_name)
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def storages_list(self, message):
        print('storage get request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        storages_request = StorageListMessage(self.server_exchange, self.server_name)
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def storages_update(self, message):
        print('storage get request message received', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        storages_request = StorageUpdateMessage(self.server_exchange, self.server_name)
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_set_recording(self, message):
        print('storage get request', flush=True)
        print('message', message, flush=True)
        uuid = message['uuid']
        print(uuid, flush=True)

        cameras_request = CameraSetRecordingMessages(self.server_exchange, self.server_name)
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_delete(self, message):
        print('cameras delete request', flush=True)

        cameras_request = CameraDeleteMessages(self.server_exchange, self.server_name)
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_ptz_move_horizontal(self, message):
        print('horizontal control request', flush=True)

        cameras_request = PanControlMessage(self.server_exchange, self.server_name)
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_ptz_move_vertical(self, message):
        print('vertical control request', flush=True)

        cameras_request = TiltControlMessage(self.server_exchange, self.server_name)
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def camera_ptz_zoom(self, message):
        print('zoom control request', flush=True)

        cameras_request = ZoomControlMessage(self.server_exchange, self.server_name)
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def archive_video(self, message):
        print('archive video request', flush=True)

        cameras_request = VideosGetMessage(self.server_exchange, self.server_name)
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_event(self, message):
        print('cameras event request', flush=True)

        cameras_request = EventsSendMessage(self.server_exchange, self.server_name)
        cameras_request.handle_request(message)
        print('message ok', flush=True)


if __name__ == '__main__':

    # cameras_ids = list(Camera.objects.all().values_list('uid', flat=True))
    # storages_ids = list(Storage.objects.all().values_list('id', flat=True))
    # print('cameras', cameras_ids, flush=True)
    # print('storages', storages_ids, flush=True)
    #
    # for cam_id in cameras_ids:
    #     camera_receiver = PikaHandler()
    #     camera_receiver.set_object_exchange(object_type='camera', object_id=cam_id)
    #     camera_receiver.start()
    #
    # for storage_id in storages_ids:
    #     storage_receiver = PikaHandler()
    #     storage_receiver.set_object_exchange(object_type='storage', object_id=storage_id)
    #     storage_receiver.start()
    # else:
    receiver = PikaHandler()
    receiver.start()
