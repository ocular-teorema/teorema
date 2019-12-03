import os
#import psutil
import subprocess
import json
from supervisor.xmlrpc import SupervisorTransport
from xmlrpc import client as xmlrpc_client
from queue_api.common import QueueEndpoint, get_supervisor_processes
from theorema.cameras.models import Server


class StatusMessages(QueueEndpoint):

    response_topic = '/status/response'
    response_message_type = 'status_response'

    def handle_request(self, params):
        print('message received', flush=True)
        self.send_response(params)
        return {'message received'}

    def send_response(self, params):
        print('sending message', flush=True)
        request_uid = params['request_uid']

        # hardware info
        local_ip_address = Server.objects.all().first().address

        uptime_job = subprocess.Popen(
            '/usr/bin/uptime',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        uptime_stdout, uptime_stderr = uptime_job.communicate()
        uptime_response = uptime_stdout.decode().split('  ')
        uptime = uptime_response[0][:-1]

        load_average = os.getloadavg()

        # cpu_usage = int(psutil.cpu_percent())
        cpu_usage = int(32)
        default_archive_path = '/home/_VideoArchive'
        # disk_usage = int(psutil.disk_usage(default_archive_path).percent)
        disk_usage = 2

        hw_info = {
            'local_ip_address': local_ip_address,
            'ocular_version': 'v1.0.0',
            'uptime': uptime,
            'load_average': load_average,
            'cpu_utilization_perc': cpu_usage,
            'disk_usage_pec': disk_usage,
            'default_archive_path': default_archive_path

        }

        supervisor_processes = get_supervisor_processes()

        message = {
            'request_uid': request_uid,
            'type': self.response_message_type,
            'data': {
                'hardware': hw_info,
                'services': supervisor_processes['services'],
                'cameras': supervisor_processes['cameras']
            }
        }
        self.send_in_queue(json.dumps(message))

        return {'message sended'}
