import json
import pika


class QueueEndpoint:
    pass


def send_in_queue(routing_key, message):
    connection = pika_setup_connection()

    channel = connection.channel()
    channel.exchange_declare(exchange='ocular', exchange_type='topic')

    message = message
    channel.basic_publish(
        exchange='ocular',
        routing_key=routing_key,
        body=message,
#        properties=pika.BasicProperties(type=type)
    )
    print("sent message %r:%r" % (routing_key, message))
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
