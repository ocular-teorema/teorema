from theorema.orgs.models import Organization
from theorema.cameras.models import Storage

from queue_api.common import QueueEndpoint, get_supervisor_processes


class ConfigurationQueueEndpoint(QueueEndpoint):
    pass

class ConfigExportMessage(ConfigurationQueueEndpoint):
    def handle_request(self, message):
        print('configuration export message received')
        self.send_response(message)

    def send_response(self, message):
        self.uuid = message['uuid']

        supervisor_cameras = get_supervisor_processes()['cameras']
        organizations = list(Organization.objects.all())

        response_data = {
            'organizations': []
        }

        for org in organizations:

            org_name = org.name

            servers = org.server_set.all()

            server_list = []
            for serv in servers:

                server_id = 'id'
                server_name = str(server_id)

                cameras = serv.camera_set.all()

                camera_dict = {}
                for camera in cameras:

                    stream_address = 'rtmp://{host}:1935/vasrc/{id}'.format(host=serv.address, id=camera.uid)
                    status = None

                    for x in supervisor_cameras:
                        if x['id'] == camera.uid:
                            status = x['status']

                    camera_data = {
                        'name': camera.name,
                        'address_primary': camera.address,
                        'address_secondary': None,
                        'storage_id': camera.storage.id,
                        'schedule_id': None,
                        'storage_days': camera.storage_life,
                        'analysis_type': camera.analysis,
                        'stream_address': stream_address,
                        'status': status,
                        'enabled': camera.is_active,
                    }

                    camera_dict[camera.uid] = camera_data

                    storages = Storage.objects.all()
                    storage_dict = {}
                    for storage in storages:
                        storage_data = {
                            'name': storage.name,
                            'path': storage.path
                        }
                        storage_dict[storage.id] = storage_data

                    #schedules = Schedule.objects.all()
                    schedule_dict = {}

                server_data = {
                    'server_id': server_id,
                    'server_name': server_name,
                    'cameras': camera_dict,
                    'storages': storage_dict,
                    'schedules': schedule_dict
                }

                server_list.append(server_data)

            org_data = {
                'name': org_name,
                'servers': server_list
            }

            response_data['organizations'].append(org_data)

        print('export data', response_data, flush=True)
        self.send_data_response(response_data)









class ConfigurationImportQueueEndpoint(QueueEndpoint):
    request_required_params = [
        'organizations'
    ]

    def handle_request(self, message):
        data = message['data']
        print('params', data, flush=True)

        if self.check_request_params(data):
            return




