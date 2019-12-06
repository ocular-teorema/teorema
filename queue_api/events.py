from queue_api.common import QueueEndpoint
import json
from queue_api.common import base_send_in_queue


class EventQueueEndpoint(QueueEndpoint):
    pass


class EventsSendMessage(QueueEndpoint):
    response_topic = '/cameras/events'
    response_message_type = 'cameras_event'

    def handle_request(self, params):
        print('message received', flush=True)

        print('params', params['data'], flush=True)

        end_of_dict = params['data'].decode().index('}')
        data = json.loads(params['data'].decode()[:end_of_dict + 1])

        message = {
            'type': self.response_message_type,
            'camera_id': data['archiveStartHint'].split('/')[1],
            'data': {
                'event_id': data['id'],
                'event_start_timestamp': data['start_timestamp'],
                'event_end_timestamp': data['end_timestamp'],
                'event_type': data['type'],
                'confidence': data['confidence'],
                'reaction': data['reaction']
            }
        }

        base_send_in_queue(self.response_exchange, json.dumps(message))


