import os
#import psutil
import subprocess
import json
from supervisor.xmlrpc import SupervisorTransport
from xmlrpc import client as xmlrpc_client
from queue_api.common import QueueEndpoint, send_in_queue
from theorema.cameras.models import Server


class StatusMessages(QueueEndpoint):

    response_topic = 'ocular/{server_name}/status/response'

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

#        cpu_usage = psutil.cpu_percent()
        default_archive_path = '/home/_VideoArchive'
#        disk_usage = psutil.disk_usage(default_archive_path)

        hw_info = {
            'local_ip_address': local_ip_address,
            'ocular_version': 'v1.0.0',
            'uptime': uptime,
            'load_average': load_average,
#            'cpu_utilization_perc': cpu_usage,
#            'disk_usage_pec': disk_usage,
            'default_archive_path': default_archive_path

        }

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

        message = {
            'request_uid': request_uid,
            'hardware': hw_info,
            'services': services,
            'cameras': cameras
        }
        send_in_queue(self.response_topic, json.dumps(message))

        return {'message sended'}
