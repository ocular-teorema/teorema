import json
import pika

from queue_api.errors import RequiredParamError


class QueueEndpoint:

    request_uid = None
    response_topic = None
    request_required_params = None

    def check_request_params(self, actual):
        actual_keys = actual.keys()
        for param in self.request_required_params:
            if param not in actual_keys:
                message = RequiredParamError(param, self.request_uid)
                self.send_error_response(message)
                return False

        return True


    def send_success_response(self):
        message = {
            'success': True,
            'request_uid': self.request_uid
        }
        send_in_queue(self.response_topic, json.dumps(message))

    def send_error_response(self, message):
        message.request_uid = self.request_uid
        send_in_queue(self.response_topic, str(message))


def send_in_queue(routing_key, message):
    connection = pika_setup_connection()

    channel = connection.channel()
    channel.exchange_declare(exchange='ocular', exchange_type='topic')

    channel.basic_publish(
        exchange='ocular',
        routing_key=routing_key,
        body=message,
        # properties=pika.BasicProperties(type=type)
    )
    print("sent message %r:%r" % (routing_key, message), flush=True)
    connection.close()


def pika_setup_connection():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        # 'localhost',
        '10.10.110.1',
        5672,
        'ocular',
        pika.PlainCredentials('ocular', 'ocular'),
        # heartbeat_interval=heartbeat
    ))
    return connection
