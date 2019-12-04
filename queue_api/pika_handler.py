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
from queue_api.common import pika_setup_connection, exchange_from_server_name, exchange_with_camera_name, exchange_with_storage_name

base_topics = [
#    '/cameras/add/request',
#    '/cameras/list/request',
    '/cameras/{cam_id}/delete/request',
    '/status/request',
#    'ocular.server_name.cameras'
]

class SelfPublished(Exception):
    pass


class PikaHandler(threading.Thread):

    def __init__(self):
        super().__init__()

        self.server_name = uuid.getnode()
        print('server name: {name}'.format(name=self.server_name), flush=True)

        self.server_exchange = exchange_from_server_name(self.server_name)
        print('exchange:', self.server_exchange, flush=True)

        self.is_object_exchange = False

    def set_object_exchange(self, object_type, object_id):

        if object_type == 'camera':
            self.server_exchange = exchange_with_camera_name(self.server_exchange, object_id)
        elif object_type == 'storage':
            self.server_exchange = exchange_with_storage_name(self.server_exchange, object_id)

        self.is_object_exchange = True
        print('set object topic:', self.server_exchange, flush=True)

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
            if not properties.app_id or int(properties.app_id) != self.server_name:
                message = json.loads(body.decode())
                message_type = message['type']
                getattr(self, message_type, self.unknown_handler)(message)
            else:
                print('message published by self, skipping', flush=True)
                raise SelfPublished

            # routing_key = method.routing_key[1:].split('/')
            # route_attr = '_'.join(routing_key)
            # print('topic obj:', self.topic_object, flush=True)
            # if self.topic_object is not None:
            #     route_attr = route_attr.replace(self.topic_object + '_', '')
            # print('route:', route_attr, flush=True)
        except SelfPublished:
            pass
        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())),
                  flush=True)
        else:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def unknown_handler(self, message):
        print('unknown message', message, flush=True)

    def cameras_add_request(self, message):
        print('camera add request message received', flush=True)

        camera_message = CameraAddMessages(self.server_name)
        camera_message.handle_request(message)
        print('message ok', flush=True)

    def cameras_list_request(self, message):
        print('camera list request message received', flush=True)

        camera_message = CameraListMessages(self.server_name)
        camera_message.handle_request(message)
        print('message ok', flush=True)

    def cameras_update_request(self, message):
        print('camera update request message received', flush=True)

        camera_message = CameraUpdateMessages(self.server_name)
        camera_message.handle_request(message)
        print('message ok')

    def status_request(self, message):
        print('status request message received', flush=True)

        status_request = StatusMessages(self.server_name)
        status_request.handle_request(message)
        print('message ok', flush=True)

    def storages_add_request(self, message):
        print('storage add request message received', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        storages_request = StorageAddMessages(self.server_name)
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def storages_delete_request(self, message):
        print('storage delete request message received', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        storages_request = StorageDeleteMessage(self.server_name)
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def storages_list_request(self, message):
        print('storage get request message received', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        storages_request = StorageListMessage(self.server_name)
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def storages_update_request(self, message):
        print('storage get request message received', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        storages_request = StorageUpdateMessage(self.server_name)
        storages_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_set_recordin_response(self, message):
        print('storage get request', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        cameras_request = CameraSetRecordingMessages(self.server_name)
        cameras_request.handle_request(message)
        print('message ok', flush=True)

    def cameras_delete_request(self, message):
        print('storage get request', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        cameras_request = CameraDeleteMessages(self.server_name, self.topic_object)
        cameras_request.handle_request(message)
        print('message ok', flush=True)


if __name__ == '__main__':

    cameras_ids = list(Camera.objects.all().values_list('uid', flat=True))
    storages_ids = list(Storage.objects.all().values_list('id', flat=True))
    print('cameras', cameras_ids, flush=True)
    print('storages', storages_ids, flush=True)

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
    #     receiver = PikaHandler()
    #     receiver.start()
    receiver = PikaHandler()
    receiver.start()