from queue_api.common import QueueEndpoint
import json
from queue_api.common import base_send_in_queue
from theorema.cameras.models import Server


class EventQueueEndpoint(QueueEndpoint):
    def __init__(self, exchange, server_name, topic_object=None):
        super().__init__(exchange=exchange, server_name=server_name, topic_object=topic_object)
        self.default_serv = Server.objects.all().first()


class EventsSendMessage(EventQueueEndpoint):
    response_topic = '/cameras/events'
    response_message_type = 'cameras_event'

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params['data'], flush=True)

        end_of_dict = params['data'].index('}')
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

        base_send_in_queue(self.exchange, message, self.default_serv.address)


