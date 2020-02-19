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
