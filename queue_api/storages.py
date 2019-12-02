from queue_api.common import QueueEndpoint, send_in_queue
from theorema.cameras.serializers import StorageSerializer, Storage

from queue_api.errors import RequestParamValidationError, RequiredParamError
import json


class StorageAddMessages(QueueEndpoint):
    request_required_params = [
        'name',
        'path',
    ]

    response_topic = 'ocular/server_name/storages/add/request'

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

        # if not self.check_request_params(params):
        #     return

        serializer_params = {
            'name': params['storage']['name'],
            'path': params['storage']['path']
        }

        serializer = StorageSerializer(data=serializer_params)
        if serializer.is_valid():
            storage = serializer.save()
            storage.save()
        else:
            # raise Exception('serializer is wrong')
            errors = serializer.errors
            msg = RequiredParamError('Validation error: "err"'.format(err=errors))
            self.send_error_response(msg)
            return

        self.send_success_response()
        return {'message sent'}


class StorageDeleteMessage(QueueEndpoint):
    request_required_params = [
        'id'
    ]

    response_topic = 'ocular/server_name/storages/delete/request'

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

        # if not self.check_request_params(params):
        #     return

        storage = Storage.objects.filter(id=params['id']).first()
        if storage:
            storage.delete()
        else:
            # raise Exception('storage does not exist')
            msg = RequiredParamError('Validation error: "err"'.format(err=errors))
            self.send_error_response(msg)
            return

        self.send_success_response()
        return {'message sent'}


class StorageListMessage(QueueEndpoint):

    response_topic = 'ocular/server_name/storages/list/request'

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

    response_topic = 'ocular/server_name/storages/update/request'

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params, flush=True)

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
            else:
                errors = serializer.errors
                msg = RequiredParamError('Validation error: "err"'.format(err=errors))
                self.send_error_response(msg)
                return
        else:
            # raise Exception('storage does not exist')
            msg = RequiredParamError('Validation error: "err"'.format(err=errors))
            self.send_error_response(msg)
            return

        send_in_queue(self.response_topic, json.dumps(message))
        return {'message sent'}

