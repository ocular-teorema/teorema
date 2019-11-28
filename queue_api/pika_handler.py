import queue
import pika
import os
import sys
import traceback
import threading
import json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theorema.settings')
import django
django.setup()

from queue_api.status import StatusMessages
from queue_api.storages import StorageMessages
from queue_api.common import pika_setup_connection


class PikaHandler(threading.Thread):

    def __init__(self):
        super().__init__()

    def callback(self, ch, method, properties, body):
        print('received', body, properties, method, flush=True)
        try:
            message = json.loads(body.decode())
            getattr(self, properties.type, self.unknown_handler)(message)
        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())),
                  flush=True)
        else:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def unknown_handler(self, message):
        print('unknown message', message, flush=True)

    def run(self):
        connection = pika_setup_connection()

        channel = connection.channel()
        channel.queue_declare(
            queue='status',
            durable=True,
            auto_delete=False,
            exclusive=False
        )
        channel.basic_consume(
            'status',
            self.callback,
        )

        print('receiver start', flush=True)
        channel.start_consuming()

    def status_request(self, message):
        print('status request message received', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        status_request = StatusMessages()
        status_request.handle_request(message)
        print('message ok', flush=True)

    def storage_add_request(self, message):
        print('storage add request', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        status_request = StorageMessages()
        status_request.handle_add_request(message)
        print('message ok', flush=True)

    def storage_delete_request(self, message):
        print('storage delete request', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        status_request = StorageMessages()
        status_request.handle_delete_request(message)
        print('message ok', flush=True)

    def storage_get_request(self, message):
        print('storage get request', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        status_request = StorageMessages()
        status_request.handle_get_request(message)
        print('message ok', flush=True)



pika_handler = PikaHandler()
pika_handler.start()
