import os
import json
import requests

from theorema.orgs.models import Organization
from theorema.cameras.models import Camera, Server, Storage, CameraSchedule
from theorema.users.models import CamSet

from queue_api.common import QueueEndpoint, get_supervisor_processes
from queue_api.messages import RequestParamValidationError, ConfigImportOrgsCountError, ConfigImportServerCountError, \
    ConfigImportServerMacError, ConfigImportServerNameError, ConfigImportInvalidPathError, \
    ConfigImportCameraStorageInvalidError
from theorema.cameras.serializers import CameraSerializer


class ConfigurationQueueEndpoint(QueueEndpoint):

    def __init__(self, scheduler=None):
        super().__init__()
        self.scheduler = scheduler


class ConfigExportMessage(ConfigurationQueueEndpoint):
    response_message_type = 'config_export'

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

                camera_list = []
                for camera in cameras:

                    stream_address = 'rtmp://{host}:1935/vasrc/{id}'.format(host=serv.address, id=camera.time_uuid)
                    status = None

                    try:
                        status = supervisor_cameras[camera.time_uuid]['status']
                    except KeyError:
                        status = 'DISABLED'

                    camera_data = {
                        'camera_id': camera.time_uuid,
                        'camera_digit': camera.uuid,
                        'name': camera.name,
                        'address_primary': camera.address,
                        'address_secondary': camera.address_secondary,
                        'storage_id': camera.storage.id if camera.storage is not None else None,
                        'schedule_id': camera.schedule.id if camera.schedule is not None else None,
                        'storage_days': camera.storage_life,
                        'analysis_type': camera.analysis,
                        'stream_address': stream_address,
                        'status': status,
                        'enabled': camera.is_active,
                        'onvif_settings': {
                            'port': camera.onvif_port,
                            'username': camera.onvif_username,
                            'password': camera.onvif_password
                        }
                    }

                    camera_list.append(camera_data)

                storages = Storage.objects.all()
                storage_list = []
                for storage in storages:
                    storage_data = {
                        'id': storage.id,
                        'name': storage.name,
                        'path': storage.path
                    }
                    storage_list.append(storage_data)

                all_schedules = CameraSchedule.objects.all()

                schedule_weekdays_list = []
                schedules_weekdays = all_schedules.filter(schedule_type='weekdays')
                for schedule in schedules_weekdays:
                    schedule_data = {
                        'id': schedule.id,
                        'days': [int(day) for day in schedule.weekdays.split(', ')]
                    }
                    schedule_weekdays_list.append(schedule_data)

                schedule_timestamp_list = []
                schedules_timestamp = all_schedules.filter(schedule_type='timestamp')
                for schedule in schedules_timestamp:
                    schedule_data = {
                        'id': schedule.id,
                        'start_timestamp': schedule.start_timestamp,
                        'stop_timestamp': schedule.stop_timestamp
                    }
                    schedule_timestamp_list.append(schedule_data)

                schedule_time_list = []
                schedules_time = all_schedules.filter(schedule_type='time_period')
                for schedule in schedules_time:
                    schedule_data = {
                        'id': schedule.id,
                        'start_time': schedule.start_daytime,
                        'stop_time': schedule.stop_daytime
                    }
                    schedule_time_list.append(schedule_data)

                schedule_data = {
                    'weekdays': schedule_weekdays_list,
                    'timestamp': schedule_timestamp_list,
                    'time_period': schedule_time_list
                }

                server_data = {
                    'server_id': server_id,
                    'server_name': server_name,
                    'cameras': camera_list,
                    'storages': storage_list,
                    'schedules': schedule_data
                }

                server_list.append(server_data)

            org_data = {
                'name': org_name,
                'servers': server_list
            }

            response_data['organizations'].append(org_data)

        # print('export data', response_data, flush=True)
        self.send_data_response(response_data)


class ConfigImportMessage(ConfigurationQueueEndpoint):
    request_required_params = [
        'organizations'
    ]
    response_message_type = 'config_import'

    schema = {
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "properties": {
                    "organizations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "servers": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "server_id": {"type": "string"},
                                            "server_name": {"type": "string"},
                                            "cameras": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "camera_digit": {"type": "number"},
                                                        "name": {"type": "string"},
                                                        "address_primary": {"type": "string"},
                                                        "address_secondary": {"type": "string"},
                                                        "analysis_type": {
                                                            "type": "number",
                                                            "enum": [1, 2, 3]
                                                        },
                                                        "storage_days": {
                                                            "type": "number",
                                                            "enum": [7, 14, 30, 1000]
                                                        },
                                                        "storage_id": {"type": "number"},
                                                        "schedule_id": {"type": "number"},
                                                        "enabled": {"type": "boolean"},
                                                        "onvif_settings": {
                                                            "type": "object",
                                                            "properties": {
                                                                "port": {"type": "number"},
                                                                "username": {"type": "string"},
                                                                "password": {"type": "string"}
                                                            },
                                                            "required": ["port"]
                                                        }
                                                    },
                                                    "required": ["camera_digit", "name", "address_primary", "analysis_type",
                                                                 "storage_days", "onvif_settings"]
                                                }
                                            },
                                            "storages": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "path": {"type": "string"},
                                                    },
                                                    "required": ["name", "path"]
                                                }
                                            },
                                            "schedules": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "schedule_type": {
                                                            "type": "string",
                                                            "enum": ["weekdays", "timestamp", "time_period"]
                                                        },
                                                        "days": {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "number",
                                                                "enum": [1, 2, 3, 4, 5, 6, 7]
                                                            }
                                                        },
                                                        "start_timestamp": {"type": "string"},
                                                        "stop_timestamp": {"type": "string"},
                                                        "start_time": {"type": "string"},
                                                        "stop_time": {"type": "string"}
                                                    },
                                                    "required": ["schedule_type"]
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "required": ["organizations"]
            }
        },
        "required": ["data"]
    }

    def handle_request(self, message):

        self.uuid = message['uuid']

        if self.check_request_params(message):
            return

        data = message['data']
        self.try_log_params(data)


        organizations = data['organizations']
        if len(organizations) > 1:
            org_error = ConfigImportOrgsCountError(self.uuid)
            self.send_error_response(org_error)
            return

        for org_dict in organizations:

            org = self.default_org
            org.name = org_dict['name']
            org.save()

            servers = org_dict['servers']
            if len(servers) > 1:
                server_error = ConfigImportServerCountError(self.uuid)
                self.send_error_response(server_error)
                return

            for server_dict in servers:
                server_id = server_dict['server_id']
                if server_id != self.default_serv.mac_address:
                    mac_error = ConfigImportServerMacError(self.uuid)
                    self.send_error_response(mac_error)
                    return

                server_name = server_dict['server_name']
                if str(server_name) != str(server_id):
                    name_mac_error = ConfigImportServerNameError(self.uuid)
                    self.send_error_response(name_mac_error)
                    return

                storage_id_map = {}

                storages = server_dict['storages']
                for storage in storages:
                    path = storage['path']
                    if not os.access(path, os.W_OK):
                        path_error = ConfigImportInvalidPathError(storage['name'], path, self.uuid)
                        self.send_error_response(path_error)
                        return

                    if storage['name'] == 'default' and path != self.default_storage.path:
                        imported_storage = self.default_storage
                        imported_storage.path = storage['path']
                    else:
                        imported_storage = Storage(name=storage['name'], path=path)

                    imported_storage.save()
                    storage_id_map[storage['id']] = imported_storage.id

                schedules = server_dict['schedules']
                for schedule in schedules:
                    schedule_type = schedule['schedule_type']
                    days = str(schedule['days'])[1:-1] if 'days' in schedule else None
                    start_timestamp = schedule['start_timestamp'] if 'start_timestamp' in schedule else None
                    stop_itmestamp = schedule['stop_timestamp'] if 'stop_timestamp' in schedule else None
                    start_time = schedule['start_time'] if 'start_time' in schedule else None
                    stop_time = schedule['stop_time'] if 'stop_time' in schedule else None

                    schedule = CameraSchedule(
                        schedule_type=schedule_type,
                        weekdays=days,
                        start_timestamp=start_timestamp,
                        stop_timestamp=stop_itmestamp,
                        start_daytime=start_time,
                        stop_daytime=stop_time
                    )

                    schedule.save()

                cameras = server_dict['cameras']
                for camera in cameras:

                    storage_indefinitely = True if camera['storage_days'] == 1000 else False
                    compress_level = 1

                    if 'storage_id' in camera:
                        old_storage_id = camera['storage_id']
                        linked_storage_id = storage_id_map[old_storage_id]
                        storage = Storage.objects.filter(id=linked_storage_id).first()
                        if not storage:
                            error = ConfigImportCameraStorageInvalidError(camera['id'], linked_storage_id, self.uuid)
                            self.send_error_response(error)
                            return
                    else:
                        storage = self.default_storage

                    serializer_params = {
                        'uuid': camera['camera_digit'],
                        'name': camera['name'],
                        'organization': org,
                        'server': self.default_serv,
                        'camera_group': 'default',
                        'address': camera['address_primary'],
                        'address_secondary': camera['address_secondary'] if 'address_secondary' in camera else None,
                        'analysis_type': camera['analysis_type'],
                        'storage_life': camera['storage_days'],
                        'indefinitely': storage_indefinitely,
                        'compress_level': compress_level,
                        'archive_path': storage.path,
                        'from_queue_api': True,
                        'onvif_port': camera['onvif_settings']['port'],
                        'onvif_username': camera['onvif_settings']['username'] if 'username' in camera[
                            'onvif_settings'] else None,
                        'onvif_password': camera['onvif_settings']['password'] if 'password' in camera[
                            'onvif_settings'] else None
                    }

                    camera_serializer = CameraSerializer(data=serializer_params)

                    if camera_serializer.is_valid():
                        imported_camera = camera_serializer.save()
                        imported_camera.storage = storage
                        imported_camera.save()
                    else:
                        errors = camera_serializer.errors
                        error_str = 'Validation error: {err}'.format(err=errors)
                        msg = RequestParamValidationError(error_str, self.uuid, self.response_message_type)
                        print(msg, flush=True)
                        self.send_error_response(msg)
                        return

        self.send_success_response()


class ConfigurationResetMessage(ConfigurationQueueEndpoint):
    response_message_type = 'reset_response'

    def handle_request(self, params):
        print('reset message received', flush=True)
        self.send_response(params)

    def send_response(self, params):
        print('sending message', flush=True)
        print('params', params, flush=True)

        all_cameras = Camera.objects.all()
        for camera in all_cameras:
            try:
                # camera = Camera.objects.get(uid=self.uuid)
                worker_data = {'id': camera.id, 'type': 'cam', 'add_time': camera.add_time}
                raw_response = requests.delete('http://{}:5005'.format(camera.server.address), json=worker_data)
                worker_response = json.loads(raw_response.content.decode())

                if camera.camera_group.camera_set.exclude(id=camera.id).count() == 0:
                    camera_group_to_delete = camera.camera_group
                else:
                    camera_group_to_delete = None

                for camset in CamSet.objects.all():
                    if camera.id in camset.cameras:
                        camset.cameras.remove(camera.id)
                        camset.save()

            except Exception as e:
                # raise Exception(code=400, detail={'message': str(e)})
                msg = RequestParamValidationError(str(e))
                self.send_error_response(msg)
                return

            if worker_response['status']:
                # raise Exception(code=400, detail={'message': worker_response['message']})
                msg = RequestParamValidationError(worker_response['message'])
                self.send_error_response(msg)
                return

            if camera.schedule_job_start and camera.schedule_job_stop:
                self.scheduler.delete_schedule(
                    start_job_id=str(camera.schedule_job_start),
                    stop_job_id=str(camera.schedule_job_stop)
                )

            camera.delete()

            if camera_group_to_delete:
                camera_group_to_delete.delete()

        all_schedules = CameraSchedule.objects.all()
        for schedule in all_schedules:
            schedule.delete()

        all_storages = Storage.objects.all()

        all_storages.exclude(id=self.default_storage.id)
        for storage in all_storages:
            storage.delete()

        self.send_success_response()
