from queue_api.common import QueueEndpoint
from theorema.cameras.serializers import StorageSerializer, Storage

from queue_api.messages import RequestParamValidationError, RequiredParamError
import json


class StorageAddMessages(QueueEndpoint):
    request_required_params = [
        'name',
        'path'
    ]

    response_topic = '/storages/add/request'
    response_message_type = 'storages_add_response'

    def __init__(self, server_name):
        super().__init__(server_name=server_name)

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        checking_params = params['storage']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

        if self.check_request_params(checking_params):
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

    response_topic = '/storages/delete/request'
    response_message_type = 'storages_delete_request'

    def __init__(self, server_name):
        super().__init__(server_name=server_name)

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

        if self.check_request_params(params):
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

    response_topic = '/storages/list/request'
    response_message_type = 'storages_list_request'

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

        self.send_in_queue(json.dumps(message))
        return {'message sent'}


class StorageUpdateMessage(QueueEndpoint):
    request_required_params = [
        'name',
        'path'
    ]
    response_topic = '/storages/update/request'

    def __init__(self, server_name):
        super().__init__(server_name=server_name)

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        checking_params = params['storage']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

        if self.check_request_params(checking_params):
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

