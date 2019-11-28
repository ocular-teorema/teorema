from queue_api.common import QueueEndpoint, send_in_queue
from theorema.cameras.serializers import CameraSerializer, Camera
from admin_theorema import listener


class CameraListMessages(QueueEndpoint):

    camera_group = 'default'
    organization = 'Ocular'

    def handle_request(self, params):
        print('message received', flush=True)

        name = params['name']
        address_primary = params['address_primary']
        #address_secondary = params['address_secondary']
        analysis_type = params['analysis_type']
        storage_days = params['storage_days']
        #storage_id = params['storage_id']
        #schedule_id = params['schedule_id']

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

    def send_stop_response(self, params):
        print('sending message', flush=True)

        camera = Camera.objects.filter(uid=params['id']).first()
        if camera:
            try:
                listener.del_autostart(params['id'])
                camera.is_active = False
                camera.save()
            except:
                raise Exception('fail in stopping camera')

        message = {
            'request_uid': params['request_uid'],
            'success': True
        }

        send_in_queue(self.queue, message)

    def send_start_response(self, params):
        print('sending message', flush=True)

        camera = Camera.objects.filter(uid=params['id']).first()
        if camera:
            try:
                path = listener.get_path(params['id'])
                listener.add_autostart('cam', params['id'], path)
                camera.is_active = True
                camera.save()
            except:
                raise Exception('fail in starting camera')

        message = {
            'request_uid': params['request_uid'],
            'success': True
        }

        send_in_queue(self.queue, message)