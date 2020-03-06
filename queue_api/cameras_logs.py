from queue_api.common import QueueEndpoint
import json
from queue_api.common import base_send_in_queue
from queue_api.messages import RequestParamValidationError
from theorema.cameras.models import CameraLog, Camera
from theorema.cameras.serializers import CameraLogSerializer
import datetime


class LogsQueueEndpoint(QueueEndpoint):
    pass


class LogsSendMessage(LogsQueueEndpoint):
    response_message_type = 'cameras_logs'

    def handle_request(self, params):
        print('message received', flush=True)

        print('params', params['data'], flush=True)

        data = params['data']

        event = {
            'camera_id': 'cam' + data['camera_id'],
            'module_name': data['moduleName'],
            'error_type': data['errorType'],
            'error_message': data['errorMessage']
        }

        if CameraLogSerializer().is_valid(event):
            new_log = CameraLogSerializer().create(event)
            event['error_time'] = int(new_log.error_time.timestamp())
            base_send_in_queue(self.response_exchange, json.dumps(event))
        else:
            print('error message already exist in 5 minutes', flush=True)


class LogsGetMessage(LogsQueueEndpoint):
    response_message_type = 'cameras_logs'

    schema = {
        "type": "object",
        "properties": {
            "camera_id": {"type": "string"},
            "data": {
                "type": "object",
                "properties": {
                    "start_timestamp": {"type": "number"},
                    "stop_timestamp": {"type": "number"}
                }
            }
        },
        "required": ["camera_id", "data"]
    }

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']

        if self.check_request_params(params):
            return

        data = params['data']
        camera_id = params['camera_id']

        print('params', params, flush=True)
        start_timestamp = datetime.datetime.fromtimestamp(data['start_timestamp']) \
            if 'start_timestamp' in data else datetime.datetime.fromtimestamp(0)
        stop_timestamp = datetime.datetime.fromtimestamp(data['stop_timestamp']) \
            if 'stop_timestamp' in data else datetime.datetime.now()

        camera_logs = CameraLog.objects.using('error_logs').filter(error_time__gte=start_timestamp,
                                                                   error_time__lte=stop_timestamp,
                                                                   camera_id=camera_id).order_by('error_time')
        if Camera.objects.filter(uid=camera_id).first():
            log_serializer = CameraLogSerializer()
            result = []
            for log in camera_logs:
                result.append(log_serializer.to_representation(log))
            self.send_data_response(result)
            return {'message sent'}
        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=camera_id))
            self.send_error_response(error)
            return
