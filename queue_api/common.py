import json
import pika


class QueueEndpoint:
    pass


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


def pika_setup_connection():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        'localhost',
        5672,
        'ocular',
        pika.PlainCredentials('ocular', 'ocular'),
#        heartbeat_interval=heartbeat
    ))
    return connection
