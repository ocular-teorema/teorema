import pika
import json

from django.core.management.base import BaseCommand
from queue_api.common import base_send_in_queue, pika_setup_connection, get_server_name

DEFAULT_ORG_NAME = 'Ocular'
DEFAULT_ADDRESS = '0.0.0.0'
DEFAULT_STORAGE_NAME = 'default'
DEFAULT_STORAGE_PATH = '/home_VideoArchive'


class Command(BaseCommand):

    def handle(self, *args, **options):
        exchange = 'driver'
        ocular_exchange = get_server_name()
        print(' [*] Request exchange is:', ocular_exchange)
        print(' [*] Response exchange is:', exchange)
        connection = pika_setup_connection()

        channel = connection.channel()
        channel.exchange_declare(exchange=exchange, exchange_type='direct')

        result = channel.queue_declare('', exclusive=True)
        queue_name = result.method.queue

        channel.queue_bind(exchange=exchange, queue=queue_name, routing_key='')

        def callback(ch, method, properties, body):
            print(" [*] Received message body: %r" % json.loads(body.decode('utf-8')))
            channel.stop_consuming()


        print(' [*] Sending test command.')

        test_connection = pika_setup_connection()
        send_channel = test_connection.channel()

        test_message = json.dumps({'type': 'status', 'uuid': "68912dc5-754e-4cd3-91ce-59f69392124e"})

        send_channel.exchange_declare(exchange=ocular_exchange, exchange_type="direct", durable=False,
                                      auto_delete=False)

        send_channel.basic_publish(
            exchange=ocular_exchange,
            routing_key='',
            body=test_message,
            properties=pika.BasicProperties()
        )

        print(" [*] Sent message to %r : %r" % (ocular_exchange, test_message), flush=True)
        test_connection.close()
        print(' [*] Receiving message.')
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
        channel.start_consuming()
