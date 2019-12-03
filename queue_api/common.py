import json
import pika
from supervisor.xmlrpc import SupervisorTransport
from xmlrpc import client as xmlrpc_client

from queue_api.errors import RequiredParamError


class QueueEndpoint:

    server_name = None
    exchange = None
    topic_object = None

    request_uid = None
    response_topic = None
    request_required_params = None

    def __init__(self, server_name, topic_object=None):
        self.server_name = server_name
        self.exchange = exchange_from_name(self.server_name)
        self.topic_object = topic_object
        # self.response_topic = self.response_topic.format(server_name=self.server_name)

    def check_request_params(self, actual):
        actual_keys = actual.keys()
        for param in self.request_required_params:
            if param not in actual_keys:
                message = RequiredParamError(param, self.request_uid)
                print(message, flush=True)
                self.send_error_response(message)
                return True

    def send_success_response(self):
        message = {
            'success': True,
            'request_uid': self.request_uid
        }
        self.send_in_queue(self.response_topic, json.dumps(message))

    def send_error_response(self, message):
        message.request_uid = self.request_uid
        self.send_in_queue(self.response_topic, str(message))

    def send_in_queue(self, routing_key, message):
        return base_send_in_queue(self.exchange, routing_key, message)


def base_send_in_queue(exchange, routing_key, message):
    connection = pika_setup_connection()

    channel = connection.channel()
    channel.exchange_declare(exchange=exchange, exchange_type='topic')

    channel.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=message,
        # properties=pika.BasicProperties(type=type)
    )
    print("sent message %r : %r : %r" % (exchange, routing_key, message), flush=True)
    connection.close()


def pika_setup_connection():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        # 'localhost',
        '10.10.110.1',
        5672,
        'ocular',
        pika.PlainCredentials('ocular', 'mC2QX0J7sx7i'),
        # heartbeat_interval=heartbeat
    ))
    return connection


def get_supervisor_processes():
    supervisor_transport = SupervisorTransport(None, None, serverurl='unix:///run/supervisor.sock')
    supervisor_proxy = xmlrpc_client.ServerProxy('http://127.0.0.1', transport=supervisor_transport)

    supervisor_processes = supervisor_proxy.supervisor.getAllProcessInfo()

    services = {}
    cameras = []
    for process in supervisor_processes:
        name = process['name']

        res = {
            'status': process['statename']
        }

        if 'cam' not in name:
            services[name] = res
        else:
            res['id'] = name
            cameras.append(res)

    return {
        'services': services,
        'cameras': cameras
    }


def exchange_from_server_name(name):
    return '/ocular/{server}'.format(server=name)


def exchange_with_camera_name(base_exchange, camera_id):
    camera_postfix = '/cameras/{camera_id}'.format(camera_id=camera_id)
    return exchange_from_server_name(base_exchange) + camera_postfix


def exchange_with_storage_name(base_exchange, storage_id):
    storage_postfix = '/storages/{storage_id}'.format(storage_id=storage_id)
    return exchange_from_server_name(base_exchange) + storage_postfix
