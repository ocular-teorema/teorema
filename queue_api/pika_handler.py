import queue
import pika
import os
import traceback
import threading
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theorema.settings')
import django
django.setup()

from queue_api.status import StatusRequest


def pika_setup_connection():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        'localhost',
        5672,
        'ocular',
        pika.PlainCredentials('ocular', 'ocular'),
        heartbeat_interval=0
    ))
    return connection


def send_in_queue(message, type, queue):
    connection = pika_setup_connection()

    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True, auto_delete=False, exclusive=False)
    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=json.dumps(message),
        properties=pika.BasicProperties(type=type)
    )
    connection.close()


class PikaHandler(threading.Thread):

    def __init__(self):
        super().__init__()

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
            self.callback,
            queue='status'
        )

        print('receiver start', flush=True)
        channel.start_consuming()

    def status_request(self, message):
        print('status request message received', flush=True)
        print('message', message, flush=True)
        request_uid = message['request_uid']
        print(request_uid, flush=True)

        status_request = StatusRequest()
        status_request.get(message)
        print('message ok', flush=True)

