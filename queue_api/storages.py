from queue_api.common import QueueEndpoint
from theorema.cameras.serializers import StorageSerializer, Storage, CameraSerializer, Camera

from queue_api.messages import RequestParamValidationError, RequiredParamError
import json


class StorageQueueEndpoint(QueueEndpoint):
    pass


class StorageAddMessages(StorageQueueEndpoint):
    request_required_params = [
        'name',
        'path'
    ]

    response_message_type = 'storages_add_response'

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        checking_params = params['data']['storage']

        if self.check_request_params(checking_params):
            return

        serializer_params = {
            'name': checking_params['name'],
            'path': checking_params['path']
        }

        serializer = StorageSerializer(data=serializer_params)
        if serializer.is_valid():
            storage = serializer.save()
            storage.save()
        else:
            errors = serializer.errors
            msg = RequestParamValidationError('Validation error: "{err}"'.format(err=errors))
            self.send_error_response(msg)
            return

        self.send_data_response({'storage_id': storage.id, 'success': True})


class StorageDeleteMessage(StorageQueueEndpoint):

    response_message_type = 'storages_delete_response'

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']

        #if self.check_request_params(params):
        #    return

        storage = Storage.objects.filter(id=params['storage_id']).first()
        if storage:
            storage.delete()
        else:
            # raise Exception('storage does not exist')
            error = RequestParamValidationError('storage with id {id} not found'.format(id=params['storage_id']))
            self.send_error_response(error)
            return

        self.send_success_response()


class StorageListMessage(StorageQueueEndpoint):

    response_message_type = 'storages_list_response'

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']

        storages = Storage.objects.all()

        storage_list = []

        for storage in storages:
            data = {
                'id': storage.id,
                'name': storage.name,
                'path': storage.path
            }
            storage_list.append(data)

        self.send_data_response(storage_list)


class StorageUpdateMessage(StorageQueueEndpoint):
    request_required_params = [
        'name',
        'path'
    ]
    response_message_type = 'storages_update_response'

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        checking_params = params['data']['storage']

        if self.check_request_params(checking_params):
            return

        serializer_params = {
            'name': checking_params['name'],
            'path': checking_params['path']
        }

        storage = Storage.objects.filter(id=params['storage_id']).first()
        if storage:
            serializer = StorageSerializer(data=serializer_params)
            if serializer_params['name'] and serializer_params['path']:
                storage.name = serializer_params['name']
                storage.path = serializer_params['path']
                storage.save()
                for camera in Camera.objects.filter(storage=storage):
                    camera.from_queue_api = True
                    camera.save()
                    camera_repr = CameraSerializer().to_representation(camera)
                    camera_repr['archive_path'] = storage.path
                    CameraSerializer().update(camera, camera_repr)
            else:
                errors = serializer.errors
                msg = RequestParamValidationError('Validation error: "err"'.format(err=errors))
                self.send_error_response(msg)
                return
        else:
            # raise Exception('storage does not exist')
            error = RequestParamValidationError('storage with id {id} not found'.format(id=params['storage_id']))
            self.send_error_response(error)
            return

        self.send_success_response()


