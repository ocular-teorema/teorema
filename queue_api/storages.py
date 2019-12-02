from queue_api.common import QueueEndpoint, send_in_queue
from theorema.cameras.serializers import StorageSerializer, Storage

from queue_api.errors import RequestParamValidationError, RequiredParamError
import json


class StorageAddMessages(QueueEndpoint):
    request_required_params = [
        'storage'
    ]

    response_topic = 'ocular/{server_name}/storages/add/request'

    def __init__(self, server_name):
        super().__init__(server_name=server_name)

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

        if not self.check_request_params(params):
            return

        serializer_params = {
            'name': params['storage']['name'],
            'path': params['storage']['path']
        }

        serializer = StorageSerializer(data=serializer_params)
        if serializer.is_valid():
            storage = serializer.save()
            storage.save()
        else:
            errors = serializer.errors
            msg = RequestParamValidationError('Validation error: "err"'.format(err=errors))
            self.send_error_response(msg)
            return

        self.send_success_response()
        return {'message sent'}


class StorageDeleteMessage(QueueEndpoint):
    request_required_params = [
        'id'
    ]

    response_topic = 'ocular/{server_name}/storages/delete/request'

    def __init__(self, server_name):
        super().__init__(server_name=server_name)

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

        if not self.check_request_params(params):
            return

        storage = Storage.objects.filter(id=params['id']).first()
        if storage:
            storage.delete()
        else:
            # raise Exception('storage does not exist')
            error = RequestParamValidationError('storage with id {id} not found'.format(id=params['id']))
            self.send_error_response(error)
            return

        self.send_success_response()
        return {'message sent'}


class StorageListMessage(QueueEndpoint):

    response_topic = 'ocular/{server_name}/storages/list/request'

    def __init__(self, server_name):
        super().__init__(server_name=server_name)

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

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

        send_in_queue(self.response_topic, json.dumps(message))
        return {'message sent'}


class StorageUpdateMessage(QueueEndpoint):
    request_required_params = [
        'storage'
    ]
    response_topic = 'ocular/{server_name}/storages/update/request'

    def __init__(self, server_name):
        super().__init__(server_name=server_name)

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

        if not self.check_request_params(params):
            return

        serializer_params = {
            'name': params['storage']['name'],
            'path': params['storage']['path']
        }

        storage = Storage.objects.filter(id=params['storage']['id']).first()
        if storage:
            serializer = StorageSerializer(data=serializer_params)
            if serializer.is_valid():
                storage.name = params['name']
                storage.path = params['path']
            else:
                errors = serializer.errors
                msg = RequestParamValidationError('Validation error: "err"'.format(err=errors))
                self.send_error_response(msg)
                return
        else:
            # raise Exception('storage does not exist')
            error = RequestParamValidationError('storage with id {id} not found'.format(id=params['storage']['id']))
            self.send_error_response(error)
            return

        self.send_success_response()
        return {'message sent'}

