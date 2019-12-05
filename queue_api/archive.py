from queue_api.common import QueueEndpoint
import requests
from theorema.cameras.models import Server
import json


class ArchiveQueueEndpoint(QueueEndpoint):
    def __init__(self, exchange, server_name, topic_object=None):
        super().__init__(exchange=exchange, server_name=server_name, topic_object=topic_object)
        self.default_serv = Server.objects.all().first()


class VideosGetMessage(ArchiveQueueEndpoint):
    request_required_params = [
        'start_timestamp',
        'stop_timestamp',
        'cameras'
    ]

    response_topic = '/archive/video/response'
    response_message_type = 'archive_video_response'

    def handle_request(self, params):
        print('message received', flush=True)
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params['data'], flush=True)

        if self.check_request_params(params['data']):
            return

        query_params = {
            'startTs': int(params['data']['start_timestamp']) * 1000,
            'endTs': int(params['data']['stop_timestamp']) * 1000,
            'cameras': ','.join(params['data']['cameras']),
            'skip': 0 if 'skip' not in params['data'].keys() else params['data']['skip'],
            'limit': 10000 if 'limit' not in params['data'].keys() else params['data']['limit']
        }

        response = requests.get('http://{}/archive_video'.format(self.default_serv.address), params=query_params)

        data = json.loads(response.content)
        videos = {
            'id': data['id'],
            'camera': data['cam'],
            'start_timestamp': data['start_posix_time'],
            'stop_timestamp': data['end_posix_time'],
            'file_size': data['fileSize']
        }

        self.send_data_response(videos)
        return
