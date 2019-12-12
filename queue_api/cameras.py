import requests
import json

from django.core.exceptions import ObjectDoesNotExist

from theorema.users.models import CamSet

from theorema.cameras.models import Camera, Storage
from theorema.cameras.serializers import CameraSerializer

from queue_api.common import QueueEndpoint, get_supervisor_processes
from queue_api.messages import RequestParamValidationError
from queue_api.scheduler import CameraSchedule


class CameraQueueEndpoint(QueueEndpoint):

    def __init__(self, scheduler=None):
        super().__init__()
        self.scheduler = scheduler

    def scheduler_add_job(self, camera):
        self.scheduler.add_job()


class CameraAddMessages(CameraQueueEndpoint):

    response_message_type = 'cameras_add_response'

    request_required_params = [
        'name', 'address_primary',
        'analysis_type', 'storage_days'
    ]

    def handle_request(self, message):
        print('message received', flush=True)
        self.uuid = message['uuid']
        params = message['data']
        print('params', params, flush=True)

        if self.check_request_params(params):
            return

        name = params['name']
        address_primary = params['address_primary']
        analysis_type = params['analysis_type']
        storage_days = params['storage_days']

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
        if 'schedule_id' in params:
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
            'analysis': analysis_type,
            'storage_life': storage_days,
            'indefinitely': storage_indefinitely,
            'compress_level': compress_level,
            'archive_path': storage.path,
            'from_queue_api': True
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
                        days=schedule.weekdays
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

                camera.schedule_job_start = start_job
                camera.schedule_job_start = stop_job
                camera.save()

        else:
            errors = camera_serializer.errors
            error_str = 'Validation error: "err"'.format(err=errors)
            msg = RequestParamValidationError(error_str, self.uuid, self.response_message_type)
            print(msg, flush=True)
            self.send_error_response(msg)
            return

        self.send_success_response()


class CameraUpdateMessages(CameraQueueEndpoint):

    response_message_type = 'cameras_update_response'

    def handle_request(self, message):
        print('message received', flush=True)
        self.uuid = message['uuid']

        camera_id = message['camera_id']

        try:
            camera = Camera.objects.get(uid=camera_id)
            if not camera.from_queue_api:
                camera.from_queue_api = True
                camera.save()
            camera_repr = CameraSerializer().to_representation(camera)
        except ObjectDoesNotExist:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=camera_id))
            print(error, flush=True)
            self.send_error_response(error)
            return

        params = message['camera']
        print('params', params, flush=True)

        name = params['name'] if 'name' in params else camera_repr['name']
        address_primary = params['address_primary'] if 'address_primary' in params else camera_repr['address']
        analysis_type = params['analysis_type'] if 'analysis_type' in params else camera_repr['analysis_type']

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

        camera_repr['name'] = name
        camera_repr['address'] = address_primary
        camera_repr['analysis_type'] = analysis_type
        camera_repr['storage_life'] = storage_days
        camera_repr['indefinitely'] = storage_indefinitely

        CameraSerializer().update(camera, camera_repr)

#            errors = camera_serializer.errors
#            msg = RequestParamValidationError('Validation error: "err"'.format(err=errors))
#            print(msg, flush=True)
#            self.send_error_response(msg)
#            return

        self.send_success_response()


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
                cam=cam.uid
            )

            status = None
            supervisor_cameras = get_supervisor_processes()['cameras']
            for x in supervisor_cameras:
                if x['id'] == cam.uid:
                    status = x['status']

            camera_list.append({
                'id': cam.uid,
                'name': cam.name,
                'address_primary': cam.address,
                # 'address_secondary': cam.address_secondary,
                'storage_id': cam.storage.id if cam.storage is not None else 0,
                # 'schedule_id': cam.schedule.id,
                'storage_days': cam.storage_life,
                'analysis_type': cam.analysis,
                'stream_address': stream_address,
                'status': status,
                'enabled': cam.is_active
                })

        print(self.uuid, flush=True)
        print(camera_list, flush=True)

        self.send_data_response(camera_list)
        return


class CameraSetRecordingMessages(CameraQueueEndpoint):

    response_message_type = 'cameras_set_recording_response'

    request_required_params = [
        'data'
    ]

    def handle_request(self, params):
        print('preparing response', flush=True)
        self.uuid = params['uuid']
        camera_id = params['camera_id']

        if self.check_request_params(params):
            return

        try:
            camera = Camera.objects.get(uid=camera_id)
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
        CameraSerializer().update(camera, camera_repr)
        self.send_success_response()


class CameraDeleteMessages(CameraQueueEndpoint):

    response_message_type = 'cameras_delete_response'

    def handle_request(self, params):
        print('preparing response', flush=True)
        self.uuid = params['uuid']

        print('params', params, flush=True)

        self.response_topic = self.response_topic.format(cam_id=params['camera_id'])

        camera = Camera.objects.filter(uid=params['camera_id']).first()

        if camera:
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
        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=params['camera_id']))
            self.send_error_response(error)
            return

        if worker_response['status']:
            # raise Exception(code=400, detail={'message': worker_response['message']})
            msg = RequestParamValidationError(worker_response['message'])
            self.send_error_response(msg)
            return

        camera.delete()

        if camera_group_to_delete:
            camera_group_to_delete.delete()

        self.send_success_response()


def set_camera_recording(camera, recording):

    if not camera.from_queue_api:
        camera.from_queue_api = True
        camera.save()
    camera_repr = CameraSerializer().to_representation(camera)
    camera_repr['is_active'] = recording
    CameraSerializer().update(camera, camera_repr)
    return


def enable_camera(camera):
    set_camera_recording(camera, True)
    return


def disable_camera(camera):
    set_camera_recording(camera, False)
    return
