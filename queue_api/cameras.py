import requests
import json

from django.core.exceptions import ObjectDoesNotExist

from theorema.users.models import CamSet

from theorema.cameras.models import Camera, Storage, CameraSchedule
from theorema.cameras.serializers import CameraSerializer

from queue_api.common import QueueEndpoint, get_supervisor_processes, get_default_cgroup
from queue_api.messages import RequestParamValidationError


class CameraQueueEndpoint(QueueEndpoint):

    def __init__(self, scheduler=None):
        super().__init__()
        self.scheduler = scheduler

    def scheduler_add_job(self, camera):
        self.scheduler.add_job()


class CameraAddMessages(CameraQueueEndpoint):
    response_message_type = 'cameras_add_response'
    schema = {
        "type": "object",
        "properties": {
            "camera_digit": {"type": "number"},
            "data": {
                "type": "object",
                "properties": {
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
                "required": ["name", "address_primary", "analysis_type", "storage_days", "onvif_settings"]
            }
        },
        "required": ["camera_digit", "data"]
    }

    def handle_request(self, message):
        print('message received', flush=True)
        self.uuid = message['uuid']

        if self.check_request_params(message):
            return

        params = message['data']
        self.try_log_params(params)

        name = params['name']
        address_primary = params['address_primary']
        address_secondary = params['address_secondary'] if 'address_secondary' in params else None
        analysis_type = params['analysis_type']
        storage_days = params['storage_days']
        onvif_port = params['onvif_settings']['port']
        onvif_username = params['onvif_settings']['username'] if 'username' in params['onvif_settings'] else None
        onvif_password = params['onvif_settings']['password'] if 'password' in params['onvif_settings'] else None
        enabled = params['enabled'] if 'enabled' in params else True
        uuid = params['camera_digit']

        # for backward compatibility
        storage_indefinitely = True if storage_days == 1000 else False
        compress_level = 1

        storage = self.default_storage
        if 'storage_id' in params:
            storage_id = params['storage_id']
            if storage_id:
                try:
                    storage = Storage.objects.get(id=storage_id)
                except ObjectDoesNotExist:
                    error = RequestParamValidationError('storage with id {id} not found'.format(id=storage_id))
                    print(error, flush=True)
                    self.send_error_response(error)
                    return

        schedule = None
        if 'schedule_id' in params and params['schedule_id']:
            schedule_id = params['schedule_id']
            if schedule_id:
                try:
                    schedule = CameraSchedule.objects.get(id=schedule_id)
                except ObjectDoesNotExist:
                    error = RequestParamValidationError('schedule with id {id} not found'.format(id=schedule_id))
                    print(error, flush=True)
                    self.send_error_response(error)
                    return

        else:
            schedule = None

        serializer_params = {
            'name': name,
            'organization': self.default_org.id,
            'server': self.default_serv.id,
            'camera_group': self.default_camera_group,
            'address': address_primary,
            'address_secondary': address_secondary,
            'analysis': analysis_type,
            'storage_life': storage_days,
            'indefinitely': storage_indefinitely,
            'compress_level': compress_level,
            'archive_path': storage.path,
            'from_queue_api': True,
            'onvif_port': onvif_port,
            'onvif_username': onvif_username,
            'onvif_password': onvif_password,
            'uuid': uuid
            # 'storage'
        }

        camera_serializer = CameraSerializer(data=serializer_params)

        if camera_serializer.is_valid():
            camera = camera_serializer.save()
            camera.storage = storage
            camera.save()

            start_job = None
            stop_job = None
            if schedule:
                if schedule.schedule_type == 'weekdays':
                    start_job, stop_job = self.scheduler.add_weekdays_schedule(
                        camera=camera,
                        days=[int(day) for day in schedule.weekdays.split(', ')]
                    )
                elif schedule.schedule_type == 'timestamp':
                    start_job, stop_job = self.scheduler.add_timestamp_schedule(
                        camera=camera,
                        start_timestamp=schedule.start_timestamp,
                        stop_timestamp=schedule.stop_timestamp
                    )
                elif schedule.schedule_type == 'time_period':
                    start_job, stop_job = self.scheduler.add_timestamp_schedule(
                        camera=camera,
                        start_time=schedule.start_time,
                        stop_time=schedule.stop_time
                    )
                else:
                    pass

                camera.schedule_job_start = start_job.id
                camera.schedule_job_stop = stop_job.id
                camera.schedule_id = schedule.id
                camera.save()

            if not enabled:
                disable_camera(camera)

        else:
            errors = camera_serializer.errors
            error_str = 'Validation error: "err"'.format(err=errors)
            msg = RequestParamValidationError(error_str, self.uuid, self.response_message_type)
            print(msg, flush=True)
            self.send_error_response(msg)
            return

        self.send_data_response({'camera_id': camera.time_uuid, 'camera_digit': camera.uuid, 'success': True})


class CameraUpdateMessages(CameraQueueEndpoint):
    response_message_type = 'cameras_update_response'

    schema = {
        "type": "object",
        "properties": {
            "camera_digit": {"type": "number"},
            "data": {
                "type": "object",
                "properties": {
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
                    }
                },
            }
        },
        "required": ["camera_digit", "data"]
    }

    def handle_request(self, message):
        print('message received', flush=True)
        self.uuid = message['uuid']

        if self.check_request_params(message):
            return

        camera_id = message['camera_digit']

        try:
            camera = Camera.objects.get(uuid=camera_id)
            if not camera.from_queue_api:
                camera.from_queue_api = True
                camera.save()
            camera_repr = CameraSerializer().to_representation(camera)
        except ObjectDoesNotExist:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=camera_id))
            print(error, flush=True)
            self.send_error_response(error)
            return

        params = message['data']
        self.try_log_params(params)

        name = params['name'] if 'name' in params else camera_repr['name']
        address_primary = params['address_primary'] if 'address_primary' in params else camera_repr['address']
        address_secondary = params['address_secondary'] if 'address_secondary' in params else camera_repr[
            'address_secondary']
        analysis_type = params['analysis_type'] if 'analysis_type' in params else camera_repr['analysis']
        enabled = params['enabled'] if 'enabled' in params else camera_repr['is_active']
        uuid = params['camera_digit'] if 'camera_digit' in params else camera_repr['uuid']
        if 'onvif_settings' in params:
            onvif_port = params['onvif_settings']['port'] if 'port' in params['onvif_settings'] else camera_repr[
                'onvif_port']
            onvif_username = params['onvif_settings']['username'] if 'username' in params['onvif_settings'] else \
                camera_repr['onvif_username']
            onvif_password = params['onvif_settings']['password'] if 'password' in params['onvif_settings'] else \
                camera_repr['onvif_password']
        else:
            onvif_port = camera_repr['onvif_port']
            onvif_username = camera_repr['onvif_username']
            onvif_password = camera_repr['onvif_password']

        if 'storage_days' in params:
            storage_days = params['storage_days']
            storage_indefinitely = True if storage_days == 1000 else False
        else:
            storage_days = camera_repr['storage_life']
            storage_indefinitely = camera_repr['indefinitely']

        if 'storage_id' in params:
            storage_id = params['storage_id']
            if storage_id:
                try:
                    storage = Storage.objects.get(id=storage_id)
                except ObjectDoesNotExist:
                    error = RequestParamValidationError('storage with id {id} not found'.format(id=storage_id))
                    print(error, flush=True)
                    self.send_error_response(error)
                    return

                camera.storage = storage

        schedule = None
        if 'schedule_id' in params:
            if params['schedule_id']:
                schedule_id = params['schedule_id']
                if schedule_id:
                    try:
                        schedule = CameraSchedule.objects.get(id=schedule_id)
                    except ObjectDoesNotExist:
                        error = RequestParamValidationError('schedule with id {id} not found'.format(id=schedule_id))
                        print(error, flush=True)
                        self.send_error_response(error)
                        return
            elif params['schedule_id'] is None:
                if camera.schedule_job_start and camera.schedule_job_stop:
                    self.scheduler.delete_schedule(
                        start_job_id=str(camera.schedule_job_start),
                        stop_job_id=str(camera.schedule_job_stop)
                    )

                    camera.schedule_job_start = None
                    camera.schedule_job_stop = None

                    camera.save()

        start_job = None
        stop_job = None
        if schedule:
            # delete previous schedule
            if camera.schedule_job_start and camera.schedule_job_stop:
                self.scheduler.delete_schedule(
                    start_job_id=str(camera.schedule_job_start),
                    stop_job_id=str(camera.schedule_job_stop)
                )

                camera.schedule_job_start = None
                camera.schedule_job_stop = None

            if schedule.schedule_type == 'weekdays':
                start_job, stop_job = self.scheduler.add_weekdays_schedule(
                    camera=camera,
                    days=[int(day) for day in schedule.weekdays.split(', ')]
                )
                print('start job', start_job, flush=True)
                print('stop_job', stop_job, flush=True)
            elif schedule.schedule_type == 'timestamp':
                start_job, stop_job = self.scheduler.add_timestamp_schedule(
                    camera=camera,
                    start_timestamp=schedule.start_timestamp,
                    stop_timestamp=schedule.stop_timestamp
                )
            elif schedule.schedule_type == 'time_period':
                start_job, stop_job = self.scheduler.add_timestamp_schedule(
                    camera=camera,
                    start_time=schedule.start_time,
                    stop_time=schedule.stop_time
                )

            camera.schedule_job_start = start_job.id
            camera.schedule_job_stop = stop_job.id

        camera.save()

        camera_repr['name'] = name
        camera_repr['address'] = address_primary
        camera_repr['address_secondary'] = address_secondary
        camera_repr['analysis_type'] = analysis_type
        camera_repr['storage_life'] = storage_days
        camera_repr['indefinitely'] = storage_indefinitely
        camera_repr['camera_group'] = self.default_camera_group
        camera_repr['onvif_port'] = onvif_port
        camera_repr['onvif_username'] = onvif_username
        camera_repr['onvif_password'] = onvif_password
        camera_repr['is_active'] = enabled
        camera_repr['uuid'] = uuid

        CameraSerializer().update(camera, camera_repr)

        #            errors = camera_serializer.errors
        #            msg = RequestParamValidationError('Validation error: "err"'.format(err=errors))
        #            print(msg, flush=True)
        #            self.send_error_response(msg)
        #            return

        self.send_data_response({'camera_digit': camera.uuid, 'camera_id': camera.time_uuid, 'success': True})


class CameraListMessages(QueueEndpoint):
    response_message_type = 'cameras_list_response'

    def handle_request(self, params):
        print('message received', flush=True)
        self.send_response(params)

    def send_response(self, params):
        print('preparing response', flush=True)
        self.uuid = params['uuid']

        all_cameras = Camera.objects.all()

        camera_list = []
        for cam in all_cameras:
            stream_address = 'rtmp://{host}:1935/vasrc/{cam}'.format(
                host=cam.server.address,
                cam=cam.time_uuid
            )

            supervisor_cameras = get_supervisor_processes()['cameras']

            try:
                status = supervisor_cameras[cam.uuid]['status']
            except KeyError:
                status = 'DISABLED'
            # for x in supervisor_cameras:
            #     status = x['status']
            #     if
            #     if x['id'] == cam.uid:
            #         status = x['status']
            #     else:4
            #         status = 'DISABLED'

            camera_list.append({
                'camera_id': cam.time_uuid,
                'camera_digit': cam.uuid,
                'name': cam.name,
                'address_primary': cam.address,
                # 'address_secondary': cam.address_secondary,
                'address_secondary': cam.address_secondary,
                'storage_id': cam.storage.id if cam.storage is not None else None,
                'schedule_id': cam.schedule.id if cam.schedule is not None else None,
                'storage_days': cam.storage_life,
                'analysis_type': cam.analysis,
                'stream_address': stream_address,
                'status': status,
                'enabled': cam.is_active,
                'onvif_settings': {
                    'port': cam.onvif_port,
                    'username': cam.onvif_username,
                    'password': cam.onvif_password
                }
            })

        self.send_data_response(camera_list)
        return


class CameraSetRecordingMessages(CameraQueueEndpoint):
    response_message_type = 'cameras_set_recording_response'

    schema = {
        "type": "object",
        "properties": {
            "camera_digit": {"type": "number"},
            "data": {"type": "boolean"}
        },
        "required": ["camera_digit", "data"]
    }

    def handle_request(self, params):
        print('preparing response', flush=True)
        self.uuid = params['uuid']

        if self.check_request_params(params):
            return

        camera_id = params['camera_digit']

        try:
            camera = Camera.objects.get(uuid=camera_id)
            if not camera.from_queue_api:
                camera.from_queue_api = True
                camera.save()
            camera_repr = CameraSerializer().to_representation(camera)
        except ObjectDoesNotExist:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=camera_id))
            print(error, flush=True)
            self.send_error_response(error)
            return

        recording = params['data']
        if not isinstance(recording, bool):
            error = RequestParamValidationError('parameter must be Boolean')
            print(error, flush=True)
            self.send_error_response(error)
            return

        camera_repr['is_active'] = recording
        camera_repr['camera_group'] = self.default_camera_group
        CameraSerializer().update(camera, camera_repr)
        self.send_success_response()


class CameraDeleteMessages(CameraQueueEndpoint):
    response_message_type = 'cameras_delete_response'

    schema = {
        "type": "object",
        "properties": {
            "camera_digit": {"type": "number"},
            "data": {"type": "object"}
        },
        "required": ["camera_digit", "data"]
    }

    def handle_request(self, params):
        print('preparing response', flush=True)
        self.uuid = params['uuid']

        if self.check_request_params(params):
            return

        print('params', params, flush=True)

        camera = Camera.objects.filter(uuid=params['camera_digit']).first()

        if not camera:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=params['camera_digit']))
            self.send_error_response(error)
            return
        else:
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

            camera_digit = camera.uuid
            camera_id = camera.time_uuid
            camera.delete()

            if camera_group_to_delete:
                camera_group_to_delete.delete()

        self.send_data_response({'camera_id': camera_id, 'camera_digit': camera_digit, 'success': True})


def set_camera_recording(camera, recording):
    if not camera.from_queue_api:
        camera.from_queue_api = True
        camera.save()
    camera_repr = CameraSerializer().to_representation(camera)
    camera_repr['is_active'] = recording
    camera_repr['camera_group'] = get_default_cgroup()
    CameraSerializer().update(camera, camera_repr)
    return True


def enable_camera(camera):
    set_camera_recording(camera, True)
    return True


def disable_camera(camera):
    set_camera_recording(camera, False)
    return True
