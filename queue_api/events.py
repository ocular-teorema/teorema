from queue_api.common import QueueEndpoint
import json
from queue_api.common import base_send_in_queue


class EventQueueEndpoint(QueueEndpoint):
    pass


class EventsSendMessage(EventQueueEndpoint):

    response_message_type = 'cameras_event'

    def handle_request(self, params):
        print('message received', flush=True)

        print('params', params['data'], flush=True)

        data = params['data']

        message = {
            'type': self.response_message_type,
            'camera_id': data['camera_id'],
            'data': {
                'event_id': data['id'],
                'event_start_timestamp': data['start_timestamp'],
                'event_end_timestamp': data['end_timestamp'] if data['end_timestamp'] > 0 else 0,
                'event_type': data['type'],
                'confidence': data['confidence'],
                'reaction': data['reaction'],
                'is_finished': data['isFinished'] if 'isFinished' in data else False
            }
        }

        base_send_in_queue(self.response_exchange, json.dumps(message))
