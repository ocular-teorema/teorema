from queue_api.common import QueueEndpoint
import json
from queue_api.common import base_send_in_queue
from queue_api.messages import RequestParamValidationError
from theorema.cameras.models import Camera, CameraLog


class LogsQueueEndpoint(QueueEndpoint):
    pass


class LogsSendMessage(LogsQueueEndpoint):
    response_message_type = 'cameras_logs'

    def handle_request(self, params):
        print('message received', flush=True)

        print('params', params['data'], flush=True)

        data = params['data']

        base_send_in_queue(self.response_exchange, json.dumps(data))


class LogsGetMessage(LogsQueueEndpoint):
    response_message_type = 'cameras_logs'

    schema = {
        "type": "object",
        "properties": {
            "camera_id": {"type": "string"},
            "data": {"type": "object"}
        },
        "required": ["camera_id", "data"]
    }

    def handler_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']

        if self.check_request_params(params):
            return

        print('params', params, flush=True)

        camera_logs = CameraLog.objects.using('error_logs').filter(camera_id=params['camera_id'])
        if camera_logs.count() > 1:
            result = []
            for log in camera_logs:
                result.append({
                    'camera_id': log.camera_id,
                    'add_time': log.add_time.timestamp(),
                    'error_type': log.error_type,
                    'error_code': log.error_code,
                    'error_message': log.error_message
                })
            self.send_data_response(result)
            return {'message sent'}
        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=params['camera_id']))
            self.send_error_response(error)
            return
