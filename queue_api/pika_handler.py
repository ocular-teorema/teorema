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
from queue_api.common import pika_setup_connection

base_topics = [
    'ocular/server_name/status/request',
#    'ocular.server_name.cameras'
]


class PikaHandler(threading.Thread):

    def __init__(self, base_topic):
        super().__init__()
        self.base_topic = base_topic

    def callback(self, ch, method, properties, body):
        print('received', body, properties, method, flush=True)
        try:
            message = json.loads(body.decode())
            routing_key = method.routing_key.split('/')[2:]
            method = '_'.join(routing_key)
            getattr(self, method, self.unknown_handler)(message)
        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())),
                  flush=True)
        else:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def unknown_handler(self, message):
        print('unknown message', message, flush=True)

    def run(self):
        print('starting receiver', flush=True)
        connection = pika_setup_connection()

        channel = connection.channel()
        channel.exchange_declare(exchange='ocular', exchange_type='topic')
        result = channel.queue_declare('', exclusive=True)

        queue_name = result.method.queue

        channel.queue_bind(exchange='ocular', queue=queue_name, routing_key=self.base_topic)

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=self.callback,
            auto_ack=True
        )

        print('receiver started', flush=True)
        channel.start_consuming()

    def status_request(self, message):
        print('status request message received', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        status_request = StatusMessages()
        status_request.handle_request(message)
        print('message ok', flush=True)


for topic in base_topics:
    pika_handler = PikaHandler(topic)
    pika_handler.start()
