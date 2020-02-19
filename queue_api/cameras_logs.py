from queue_api.common import QueueEndpoint
import json
from queue_api.common import base_send_in_queue


class LogsQueueEndpoint(QueueEndpoint):
    pass


class LogsSendMessage(LogsQueueEndpoint):
    response_message_type = 'cameras_logs'

    def handle_request(self, params):
        print('message received', flush=True)

        print('params', params['data'], flush=True)

        end_of_dict = params['data'].decode().index('}')
        data = json.loads(params['data'].decode()[:end_of_dict + 1])

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


