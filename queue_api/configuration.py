import os

from theorema.orgs.models import Organization
from theorema.cameras.models import Camera, Server, Storage

from queue_api.common import QueueEndpoint, get_supervisor_processes
from queue_api.messages import RequestParamValidationError, ConfigImportOrgsCountError, ConfigImportServerCountError,\
    ConfigImportServerMacError, ConfigImportServerNameError, ConfigImportInvalidPathError, ConfigImportCameraStorageInvalidError
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

                server_id = serv.mac_address
                server_name = serv.name

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

        self.uuid = message['uuid']

        data = message['data']
        print('params', data, flush=True)

        if self.check_request_params(data):
            return

        organizations = data['organizations']
        if len(organizations.keys()) > 1:
            org_error = ConfigImportOrgsCountError(self.uuid)
            self.send_error_response(org_error)

        for org_dict in organizations:

            org = self.default_org
            org.name = org_dict['name']
            org.save()

            servers = org_dict['servers']
            if len(servers.keys()) > 1:
                server_error = ConfigImportServerCountError(self.uuid)
                self.send_error_response(server_error)

            for server_dict in servers:
                server_id = server_dict['server_id']
                if server_id != self.default_serv.mac_address:
                    mac_error = ConfigImportServerMacError(self.uuid)
                    self.send_error_response(mac_error)

                server_name = server_dict['server_name']
                if str(server_name) != str(server_id):
                    name_mac_error = ConfigImportServerNameError(self.uuid)
                    self.send_error_response(name_mac_error)

                storage_id_map = {}

                storages = server_dict['storages']
                for storage_id, storage in storages.items():
                    path = storage['path']
                    if not os.access(path, os.W_OK):
                        path_error = ConfigImportInvalidPathError(storage['name'], path, self.uuid)
                        self.send_error_response(path_error)

                    if storage['name'] == 'default' and path != self.default_storage.path:
                        imported_storage = self.default_storage
                        imported_storage.path = storage['path']
                    else:
                        imported_storage = Storage(name=storage['name'], path=path)

                    imported_storage.save()
                    storage_id_map[storage_id] = imported_storage.id

                cameras = server_dict['cameras']
                for camera_id, camera in cameras.items():

                    storage_indefinitely = True if camera['storage_days'] == 1000 else False
                    compress_level = 1

                    if 'storage_id' in camera:
                        old_storage_id = camera['storage_id']
                        linked_storage_id = storage_id_map[old_storage_id]
                        storage = Storage.objects.filter(id=linked_storage_id)
                        if not storage:
                            error = ConfigImportCameraStorageInvalidError(camera_id, linked_storage_id, self.uuid)
                            self.send_error_response(error)
                            return
                    else:
                        storage = self.default_storage

                    serializer_params = {
                        'name': camera['name'],
                        'organization': org,
                        'server': self.default_serv,
                        'camera_group': 'default',
                        'address': camera['address_primary'],
                        'analysis': camera['analysis'],
                        'storage_life': camera['storage_days'],
                        'indefinitely': storage_indefinitely,
                        'compress_level': compress_level,
                        'archive_path': storage.path,
                        'from_queue_api': True
                    }

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

        self.send_success_response()




