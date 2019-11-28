from queue_api.common import QueueEndpoint, send_in_queue
from theorema.cameras.serializers import StorageSerializer, Storage


class StorageMessages(QueueEndpoint):

    queue = 'storage_queue'

    def handle_add_request(self, params):
        print('message received', flush=True)
        self.send_add_response(params)
        return {'message received'}

    def handle_delete_request(self, params):
        print('message received', flush=True)
        self.send_delete_response(params)
        return {'message received'}

    def handle_get_request(self, params):
        print('message received', flush=True)
        self.send_delete_response(params)
        return {'message received'}

    def send_add_response(self, params):
        print('sending message', flush=True)

        serializer_params = {
            'name': params['storage']['name'],
            'path': params['storage']['path']
        }

        serializer = StorageSerializer(data=serializer_params)
        if serializer.is_valid():
            storage = serializer.save()
            storage.save()
        else:
            raise Exception('serializer is wrong')

        message = {
            'request_uid': params['request_uid'],
            'success': True
        }

        send_in_queue(message, 'response', self.queue)


    def send_delete_response(self, params):
        print('sending message', flush=True)

        storage = Storage.objects.filter(name=params['name']).first()
        if storage:
            storage.delete()
        else:
            raise Exception('storage name does not exist')

        message = {
            'request_uid': params['request_uid'],
            'success': True
        }

        send_in_queue(message, 'response', self.queue)


    def send_get_response(self, params):
        print('sending message', flush=True)

        storages = Storage.objects.all()

        message = {
            'request_uid': params['request_uid'],
            'storage_list': []
        }

        for storage in storages:
            data = {
                'id': storage.id,
                'name': storage.name,
                'path': storage.path
            }
            message['storage_list'].append(data)

        send_in_queue(message, 'response', self.queue)

