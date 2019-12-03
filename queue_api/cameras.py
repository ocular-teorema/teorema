import requests
import json

from theorema.users.models import CamSet
from theorema.orgs.models import Organization
from theorema.cameras.models import CameraGroup, Server, Camera, Storage
from theorema.cameras.serializers import CameraSerializer

from queue_api.common import QueueEndpoint, get_supervisor_processes
from queue_api.errors import RequestParamValidationError


class CameraAddMessages(QueueEndpoint):

    request_required_params = [
        'name', 'address_primary',
        'analysis_type', 'storage_days'
    ]
    response_topic = '/cameras/add/response'

    def __init__(self, server_name):
        super().__init__(server_name=server_name)

        self.default_org = Organization.objects.all().first()
        self.default_serv = Server.objects.all().first()
        cgroup = CameraGroup.objects.all().first()
        if cgroup is None:
            cgroup = 'default'
        else:
            cgroup = cgroup.id
        self.default_camera_group = cgroup
        self.default_storage = Storage.objects.all().first()

    def handle_request(self, message):
        print('message received', flush=True)
        self.request_uid = message['request_uid']
        params = message['camera']
        print('request uid', self.request_uid, flush=True)
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

        if 'storage_id' in params:
            storage_id = params['storage_id']
            storage = Storage.objects.filter(id=storage_id)
            if not storage:
                error = RequestParamValidationError('storage with id {id} not found'.format(id=storage_id))
                print(error, flush=True)
                self.send_error_response(error)
                return
        else:
            storage = self.default_storage

        # disabled for now
        #
        # schedule_id = params['schedule_id']
        # address_secondary = params['address_secondary']

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
        else:
            errors = camera_serializer.errors
            msg = RequestParamValidationError('Validation error: "err"'.format(err=errors))
            print(msg, flush=True)
            self.send_error_response(msg)
            return

        self.send_success_response()
        return {'message sent'}


class CameraListMessages(QueueEndpoint):

    response_topic = '/cameras/list/response'

    def handle_request(self, params):
        print('message received', flush=True)
        self.send_response(params)
        return {'message received'}

    def send_response(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']

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
                'storage_id': cam.storage.id,
                # 'schedule_id': cam.schedule.id,
                'storage_days': cam.storage_life,
                'analysis_type': cam.analysis,
                'stream_address': stream_address,
                'status': status,
                'enabled': cam.is_active
                })

        print(self.request_uid, flush=True)
        print(camera_list, flush=True)
        message = {
            'request_uid': self.request_uid,
            'camera_list': camera_list
        }
        self.send_in_queue(self.response_topic, json.dumps(message))

        return


class CameraSetRecordingMessages(QueueEndpoint):

    response_topic = '/cameras/{cam_id}/set_recording/request'

    def __init__(self, server_name):
        super().__init__(server_name=server_name)

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

        self.response_topic = self.response_topic.format(cam_id=self.request_uid)

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:

            data = dict(CameraSerializer().basic_to_representation(camera))
            data['unique_id'] = str(camera.id) + camera.add_time
            data['ws_video_url'] = 'ws://%s/video_ws/?port=%s' % (camera.server.address, camera.port+50)
            data['thumb_url'] = 'http://%s:5005/thumb/%s/' % (camera.server.address, camera.id)
            data['rtmp_video_url'] = 'rtmp://%s:1935/vasrc/cam%s' % (camera.server.address, str(camera.id) + camera.add_time)
            data['m3u8_video_url'] = 'http://%s:8080/vasrc/cam%s/index.m3u8' % (camera.server.address, str(camera.id))
            data['camera_group'] = camera.camera_group.id
            if camera.is_active:
                data['is_active'] = False
            else:
                data['is_active'] = True
            data['server'] = camera.server
            data['organization'] = camera.organization

            CameraSerializer().update(camera, data)

        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=self.request_uid))
            self.send_error_response(error)
            return

        self.send_success_response()
        return {'message sent'}



class CameraDeleteMessages(QueueEndpoint):

    response_topic = '/cameras/{cam_id}/delete/response'

    def __init__(self, server_name, topic_object):
        super().__init__(server_name=server_name, topic_object=topic_object)

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

        self.response_topic = self.response_topic.format(cam_id=self.topic_object)

        camera = Camera.objects.filter(uid=self.request_uid).first()
        if camera:
            try:
                # camera = Camera.objects.get(uid=self.request_uid)
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
            error = RequestParamValidationError('camera with id {id} not found'.format(id=self.request_uid))
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
        return {'message sent'}
