import json
import uuid
import pika
from supervisor.xmlrpc import SupervisorTransport
from xmlrpc import client as xmlrpc_client

from queue_api.messages import QueueMessage, QueueSuccessMessage, QueueErrorMessage, RequiredParamError


class QueueEndpoint:

    server_name = None
    exchange = None
    topic_object = None

    uuid = None
    request_required_params = None
    response_exchange = '/ocular_driver'
    response_message_type = None

    def __init__(self):
        self.server_name, self.exchange = get_server_name_exchange()

    def check_request_params(self, actual):
        actual_keys = actual.keys()
        for param in self.request_required_params:
            if param not in actual_keys:
                message = RequiredParamError(param, self.uuid, self.response_message_type)
                print(message, flush=True)
                self.send_error_response(message)
                return True

    def send_data_response(self, data):
        message = QueueMessage(data=data)
        self.send_in_queue(message)

    def send_success_response(self):
        message = QueueSuccessMessage()
        self.send_in_queue(message)

    def send_error_response(self, message):
        self.send_in_queue(message)

    def send_in_queue(self, message):
        message.uuid = self.uuid
        message.response_type = self.response_message_type
        return base_send_in_queue(self.response_exchange, str(message))


def base_send_in_queue(exchange, message):
    connection = pika_setup_connection()

    channel = connection.channel()
    channel.exchange_declare(exchange=exchange, exchange_type='topic')

    channel.basic_publish(
        exchange=exchange,
        routing_key='',
        body=message,
        properties=pika.BasicProperties()
    )
    print("sent message %r : %r" % (exchange, message), flush=True)
    connection.close()


def pika_setup_connection():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        # 'localhost',
        host='10.10.110.1',
        port=5672,
        virtual_host='ocular',
        credentials=pika.PlainCredentials('ocular', 'mC2QX0J7sx7i'),
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


def get_server_name():
    return uuid.getnode()


def exchange_from_server_name(name):
    return '/ocular/{server}'.format(server=name)


def get_server_name_exchange():
    server_name = get_server_name()
    exchange = exchange_from_server_name(server_name)
    return server_name, exchange
#
# def exchange_with_camera_name(base_exchange, camera_id):
#     camera_postfix = '/cameras/{camera_id}'.format(camera_id=camera_id)
#     return base_exchange + camera_postfix
#
#
# def exchange_with_storage_name(base_exchange, storage_id):
#     storage_postfix = '/storages/{storage_id}'.format(storage_id=storage_id)
#     return base_exchange + storage_postfix
