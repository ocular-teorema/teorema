from queue_api.common import QueueEndpoint, send_in_queue
from theorema.cameras.serializers import StorageSerializer, Storage


class StorageMessages(QueueEndpoint):

    routing_keys = {
        'stop': 'ocular/{server_name}/storages/add/response',
        'start': 'ocular/{server_name}/storages/delete/response',
        'delete': 'ocular/{server_name}/storages/list/response',
        'update': 'ocular/{server_name}/storages/update/response'
    }

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
        self.send_get_response(params)
        return {'message received'}

    def handle_update_request(self, params):
        print('message received', flush=True)
        self.send_update_response(params)
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
            message = {
                'request_uid': params['request_uid'],
                'success': True
            }
        else:
            # raise Exception('serializer is wrong')
            message = {
                'request_uid': params['request_uid'],
                'success': False,
                'code': 2,
                'error': 'Some error occurred'
            }

        send_in_queue(self.routing_keys['add'], message)


    def send_delete_response(self, params):
        print('sending message', flush=True)

        storage = Storage.objects.filter(id=params['id']).first()
        if storage:
            storage.delete()
            message = {
                'request_uid': params['request_uid'],
                'success': True
            }
        else:
            # raise Exception('storage does not exist')
            message = {
                'request_uid': params['request_uid'],
                'success': False,
                'code': 2,
                'error': 'Some error occurred'
            }

        send_in_queue(self.routing_keys['delete'], message)


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

        send_in_queue(self.routing_keys['list'], message)

    def send_update_response(self, params):
        print('sending message', flush=True)

        serializer_params = {
            'name': params['storage']['name'],
            'path': params['storage']['path']
        }

        storage = Storage.objects.filter(id=params['id']).first()
        if storage:
            serializer = StorageSerializer(data=serializer_params)
            if serializer.is_valid():
                storage.name = params['name']
                storage.path = params['path']
                message = {
                    'request_uid': params['request_uid'],
                    'success': True
                }
            else:
                message = {
                    'request_uid': params['request_uid'],
                    'success': False,
                    'code': 2,
                    'error': 'Some error occurred'
                }
        else:
            # raise Exception('storage does not exist')
            message = {
                'request_uid': params['request_uid'],
                'success': False,
                'code': 2,
                'error': 'Some error occurred'
            }


        send_in_queue(self.routing_keys['update'], message)



