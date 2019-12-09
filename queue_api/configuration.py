from theorema.orgs.models import Organization
from theorema.cameras.models import Camera, Server, Storage

from queue_api.common import QueueEndpoint, get_supervisor_processes
from queue_api.messages import RequestParamValidationError
from theorema.cameras.serializers import CameraSerializer


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
                        'storage_id': camera.storage.id if camera.storage is not None else 0,
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


class ConfigImportMessage(QueueEndpoint):
    request_required_params = [
        'organizations'
    ]

    def handle_request(self, message):

        data = message['data']
        print('params', data, flush=True)

        if self.check_request_params(data):
            return

        organization = data['organizations']

        for org_dict in organization:

            org = Organization(name=org_dict['name'])
            org.save()

            servers = org_dict['servers']
            for server_dict in servers:
                server_id = server_dict['server_id']
                server_name = server_dict['server_name']

                server = Server(name=server_name, organization=org)
                server.save()

                cameras = server_dict['cameras']
                for camera in cameras:

                    storage_indefinitely = True if camera['storage_days'] == 1000 else False
                    compress_level = 1

                    serializer_params = {
                        'name': camera['name'],
                        'organization': org,
                        'server': server,
                        'camera_group': 'default',
                        'address': camera['address_primary'],
                        'analysis': camera['analysis'],
                        'storage_life': camera['storage_days'],
                        'indefinitely': storage_indefinitely,
                        'compress_level': compress_level,
                        'archive_path': storage.path,
                        'from_queue_api': True
                        # 'storage'
                    }

                    if 'storage_id' in camera:
                        storage_id = camera['storage_id']
                        storage = Storage.objects.filter(id=storage_id)
                        if not storage:
                            error = RequestParamValidationError('storage with id {id} not found'.format(id=storage_id))
                            print(error, flush=True)
                            self.send_error_response(error)
                            return
                    else:
                        storage = self.default_storage

                    camera_serializer = CameraSerializer(data=serializer_params)

                    if camera_serializer.is_valid():
                        imported_camera = camera_serializer.save()
                        imported_camera.storage = storage
                        imported_camera.save()
                    else:
                        errors = camera_serializer.errors
                        error_str = 'Validation error: "err"'.format(err=errors)
                        msg = RequestParamValidationError(error_str, self.uuid, self.response_message_type)
                        print(msg, flush=True)
                        self.send_error_response(msg)
                        return

                storages = server_dict['storages']
                for storage in storages:
                    imported_storage = Storage(name=storage['name'], path=storage['path'])
                    imported_storage.save()

        self.send_success_response()




