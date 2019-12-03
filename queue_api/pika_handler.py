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

from queue_api.status import StatusMessages
from queue_api.storages import StorageListMessage, StorageDeleteMessage, StorageAddMessages, StorageUpdateMessage
from queue_api.cameras import CameraAddMessages, CameraListMessages, CameraSetRecordingMessages, CameraDeleteMessages
from queue_api.common import pika_setup_connection, exchange_from_name

base_topics = [
    '/cameras/add/request',
    '/cameras/list/request',
    '/status/request',
#    'ocular.server_name.cameras'
]


class PikaHandler(threading.Thread):

    def __init__(self, base_topic):
        super().__init__()

        self.server_name = uuid.getnode()
        print('server name: {name}'.format(name=self.server_name), flush=True)
        self.server_exchange = exchange_from_name(self.server_name)
        print('exchange:', self.server_exchange, flush=True)

        self.base_topic = base_topic.format(server_name=self.server_name)
        print(self.base_topic, flush=True)

    def callback(self, ch, method, properties, body):
        print('received', body, properties, method, flush=True)
        try:
            message = json.loads(body.decode())
            routing_key = method.routing_key[1:].split('/')
            method = '_'.join(routing_key)
            print('method:', method, flush=True)
            getattr(self, method, self.unknown_handler)(message)
        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())),
                  flush=True)
#        else:
#            ch.basic_ack(delivery_tag=method.delivery_tag)

    def unknown_handler(self, message):
        print('unknown message', message, flush=True)

    def run(self):
        print('starting receiver', flush=True)
        connection = pika_setup_connection()
        channel = connection.channel()

        channel.exchange_declare(exchange=self.server_exchange, exchange_type='topic')
        result = channel.queue_declare('', exclusive=True)

        queue_name = result.method.queue
        channel.queue_bind(exchange=self.server_exchange, queue=queue_name, routing_key=self.base_topic)

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=self.callback,
            auto_ack=True
        )

        print('receiver started', flush=True)
        channel.start_consuming()

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

    def status_request(self, message):
        print('status request message received', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

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

    def cameras_delete_response(self, message):
        print('storage get request', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        cameras_request = CameraDeleteMessages(self.server_name)
        cameras_request.handle_request(message)
        print('message ok', flush=True)


if __name__ == '__main__':

    for topic in base_topics:
        pika_handler = PikaHandler(topic)
        pika_handler.start()
