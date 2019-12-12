import json
import sys
import os
import uuid
import pika


from supervisor.xmlrpc import SupervisorTransport
from xmlrpc import client as xmlrpc_client
from theorema.orgs.models import Organization
from theorema.cameras.models import CameraGroup, Server, Storage

from queue_api.messages import QueueMessage, QueueSuccessMessage, QueueErrorMessage, RequiredParamError
from queue_api.settings import *


class QueueEndpoint:

    server_name = None
    exchange = None
    topic_object = None

    uuid = None
    request_required_params = None
    response_exchange = RABBITMQ_RESPONSE_EXCHANGE
    response_message_type = None

    def __init__(self):
        self.server_name = get_server_name()

        self.default_org = Organization.objects.all().first()
        self.default_serv = Server.objects.all().first()
        cgroup = CameraGroup.objects.all().first()
        if cgroup is None:
            cgroup = 'default'
        else:
            cgroup = cgroup.id
        self.default_camera_group = cgroup
        self.default_storage = Storage.objects.all().first()

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
    channel.exchange_declare(exchange=exchange, exchange_type=RABBITMQ_EXCHANGE_TYPE_DRIVER, durable=False, auto_delete=False)

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
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=pika.PlainCredentials(RABBITMQ_CREDENTIALS['user'], RABBITMQ_CREDENTIALS['password']),
        # heartbeat_interval=heartbeat
    ))
    return connection


def get_supervisor_processes():
    supervisor_transport = SupervisorTransport(None, None, serverurl='unix:///run/supervisor.sock')
    supervisor_proxy = xmlrpc_client.ServerProxy('http://127.0.0.1', transport=supervisor_transport)

    supervisor_processes = supervisor_proxy.supervisor.getAllProcessInfo()

    services = {}
    cameras = {}
    for process in supervisor_processes:
        name = process['name']

        res = {
            'status': process['statename']
        }

        if 'cam' not in name:
            services[name] = res
        else:
            cameras[name] = res
            #res['id'] = name
            #cameras['id'] = (res)

    return {
        'services': services,
        'cameras': cameras
    }


def get_server_name():
    return Server.objects.all().first().name


def get_default_cgroup():
    cgroup = CameraGroup.objects.all().first()
    if cgroup is None:
        cgroup = 'default'
    else:
        cgroup = cgroup.id
    return cgroup