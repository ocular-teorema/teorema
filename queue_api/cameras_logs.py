from queue_api.common import QueueEndpoint
import json
from queue_api.common import base_send_in_queue
from queue_api.messages import RequestParamValidationError
from theorema.cameras.models import CameraLog, Camera
import datetime


class LogsQueueEndpoint(QueueEndpoint):
    pass


class LogsSendMessage(LogsQueueEndpoint):
    response_message_type = 'cameras_logs'

    def handle_request(self, params):
        print('message received', flush=True)

        print('params', params['data'], flush=True)

        data = params['data']

        error_time = datetime.datetime.now()

        event = {
            'camera_id': 'cam' + data['camera_id'],
            'error_time': error_time,
            'module_name': data['moduleName'],
            'error_type': data['errorType'],
            'error_message': data['errorMessage']
        }

        log = CameraLog(**event)
        log.save(using='error_logs')

        event['error_time'] = int(event['error_time'].timestamp())

        base_send_in_queue(self.response_exchange, json.dumps(event))


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
            result = []
            for log in camera_logs:
                result.append({
                    'camera_id': log.camera_id,
                    'error_time': int(log.error_time.timestamp()),
                    'error_type': log.error_type,
                    'module_name': log.module_name,
                    'error_message': log.error_message
                })
            self.send_data_response(result)
            return {'message sent'}
        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=camera_id))
            self.send_error_response(error)
            return
