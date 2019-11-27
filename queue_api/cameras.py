from queue_api.common import QueueEndpoint
from theorema.cameras.serializers import CameraSerializer


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
