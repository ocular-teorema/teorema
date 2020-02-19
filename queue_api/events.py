from queue_api.common import QueueEndpoint
import json
from queue_api.common import base_send_in_queue
from theorema.cameras.models import Camera


class EventQueueEndpoint(QueueEndpoint):
    pass


class EventsSendMessage(EventQueueEndpoint):

    response_message_type = 'cameras_event'

    def handle_request(self, params):
        print('message received', flush=True)

        print('params', params['data'], flush=True)

        end_of_dict = params['data'].decode().index('}')
        data = json.loads(params['data'].decode()[:end_of_dict + 1])

        is_finished = data['isFinished'] if 'isFinished' in data else False

        camera = Camera.objects.filter(time_uid=data['archiveStartHint'].split('/')[1]).first()

        message = {
            'type': self.response_message_type,
            'camera_id': camera.time_uid,
            'camera_digit': camera.uid,
            'data': {
                'event_id': data['id'],
                'event_start_timestamp': data['start_timestamp'],
                'event_end_timestamp': data['end_timestamp'] if data['end_timestamp'] > 0 else 0,
                'event_type': data['type'],
                'confidence': data['confidence'],
                'reaction': data['reaction'],
                'is_finished': is_finished
            }
        }

        base_send_in_queue(self.response_exchange, json.dumps(message))
