from queue_api.common import QueueEndpoint
import requests
from theorema.cameras.models import Server
import json


class ArchiveQueueEndpoint(QueueEndpoint):
    pass


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
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
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

        response = requests.get('http://{}:5005/archive_video'.format(self.default_serv.address), params=query_params)

        response_data = json.loads(response.content.decode())
        data = {'videos': []}
        for video in response_data:
            video_data = {
                'id': video['id'],
                'camera': video['cam'],
                'start_timestamp': video['start_posix_time'],
                'stop_timestamp': video['end_posix_time'],
                'file_size': video['fileSize']
            }
            data['videos'].append(video_data)

        self.send_data_response(data)
        return
