from queue_api.common import QueueEndpoint, send_in_queue
from theorema.cameras.serializers import CameraSerializer, Camera
import requests
import json
from theorema.users.models import CamSet


class CameraListMessages(QueueEndpoint):
    camera_group = 'default'
    organization = 'Ocular'

    routing_keys = {
        'stop': 'ocular/{server_name}/cameras/{cam_id}/delete/response',
        'start': 'ocular/{server_name}/cameras/{cam_id}/delete/response',
        'delete': 'ocular/{server_name}/cameras/{cam_id}/delete/response'
    }

    def handle_request(self, params):
        print('message received', flush=True)

        name = params['name']
        address_primary = params['address_primary']
        # address_secondary = params['address_secondary']
        analysis_type = params['analysis_type']
        storage_days = params['storage_days']
        # storage_id = params['storage_id']
        # schedule_id = params['schedule_id']

        serializer_params = {
            'name': name,
            'organization': self.organization,
            'camera_group': self.camera_group,
            'address': address_primary,
            'analysis': analysis_type,
            'storage_life': storage_days

        }

        serializer = CameraSerializer(data=serializer_params)

        if serializer.is_valid():
            camera = serializer.save()
            camera.save()
        else:
            raise Exception('serializer is wrong')

        print('camera', camera, flush=True)
        return {'message sended'}

    def handle_stop_request(self, params):
        print('message received', flush=True)
        self.send_stop_response(params)
        return {'message received'}

    def handle_start_request(self, params):
        print('message received', flush=True)
        self.send_start_response(params)
        return {'message received'}

    def handle_delete_request(self, params):
        print('message received', flush=True)
        self.send_delete_response(params)
        return {'message received'}

    def send_stop_response(self, params):
        print('sending message', flush=True)

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:

            data = dict(CameraSerializer().basic_to_representation(camera))
            data['unique_id'] = str(camera.id) + camera.add_time
            data['ws_video_url'] = 'ws://%s/video_ws/?port=%s' % (camera.server.address, camera.port+50)
            data['thumb_url'] = 'http://%s:5005/thumb/%s/' % (camera.server.address, camera.id)
            data['rtmp_video_url'] = 'rtmp://%s:1935/vasrc/cam%s' % (camera.server.address, str(camera.id) + camera.add_time)
            data['m3u8_video_url'] = 'http://%s:8080/vasrc/cam%s/index.m3u8' % (camera.server.address, str(camera.id))
            data['camera_group'] = camera.camera_group.id
            data['is_active'] = False
            data['server'] = camera.server
            data['organization'] = camera.organization

            try:
                CameraSerializer().update(camera, data)
            except:
                raise Exception('fail in camera stopping')

        message = {
            'request_uid': params['request_uid'],
            'success': True
        }

        send_in_queue(self.routing_keys['stop'], message)

    def send_start_response(self, params):
        print('sending message', flush=True)

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:

            data = dict(CameraSerializer().basic_to_representation(camera))
            data['unique_id'] = str(camera.id) + camera.add_time
            data['ws_video_url'] = 'ws://%s/video_ws/?port=%s' % (camera.server.address, camera.port + 50)
            data['thumb_url'] = 'http://%s:5005/thumb/%s/' % (camera.server.address, camera.id)
            data['rtmp_video_url'] = 'rtmp://%s:1935/vasrc/cam%s' % (
            camera.server.address, str(camera.id) + camera.add_time)
            data['m3u8_video_url'] = 'http://%s:8080/vasrc/cam%s/index.m3u8' % (camera.server.address, str(camera.id))
            data['camera_group'] = camera.camera_group.id
            data['is_active'] = True
            data['server'] = camera.server
            data['organization'] = camera.organization

            try:
                CameraSerializer().update(camera, data)
            except:
                raise Exception('fail in camera starting')

        message = {
            'request_uid': params['request_uid'],
            'success': True
        }

        send_in_queue(self.routing_keys['start'], message)

    def send_delete_response(self, params):
        print('sending message', flush=True)

        pk = params['camera_id']

        try:
            camera = Camera.objects.get(uid=pk)
            worker_data = {'id': camera.id, 'type': 'cam', 'add_time': camera.add_time}
            # worker_data = {'id': pk, 'type': 'cam'}
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
            raise Exception(code=400, detail={'message': str(e)})


        if worker_response['status']:
            raise Exception(code=400, detail={'message': worker_response['message']})

        camera.delete()

        if camera_group_to_delete:
            camera_group_to_delete.delete()

        message = {
            'request_uid': params['request_uid'],
            'success': True
        }

        send_in_queue(self.routing_keys['delete'], message)
