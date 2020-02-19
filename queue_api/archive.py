import requests
import json
import psycopg2

from theorema.cameras.models import Camera

from queue_api.common import QueueEndpoint
from queue_api.messages import RequestParamValidationError


def check_confidence(conf_low, conf_medium, conf_high):
    confidence_db = ' and confidence '

    if conf_low:
        if conf_medium:
            if not conf_high:
                confidence_db += '< 80 '
            else:
                confidence_db = ''
        else:
            confidence_db += '< 50 ' if not conf_high else 'not between 50 and 79 '
    else:
        if conf_medium:
            confidence_db += 'between 50 and 79 ' if not conf_high else '>= 50'
        else:
            if conf_high:
                confidence_db += '>= 80 '
            else:
                return False

    return confidence_db


class ArchiveQueueEndpoint(QueueEndpoint):
    schema = {
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "properties": {
                    "start_timestamp": {"type": "number"},
                    "stop_timestamp": {"type": "number"},
                    "cameras": {
                        "type": "array",
                        "items": {
                            "type": "number"
                        }
                    },
                    "skip": {"type": "number"},
                    "limit": {"type": "number"}
                },
                "required": ["start_timestamp", "stop_timestamp", "cameras"]
            }
        },
        "required": ["data"]
    }

    def prepare_camera_query(self, column, data, no_prepend_cam=False):
        camera_list = data['cameras']
        # camera_list_query = []
        # for camera in camera_list:
        #    camera = camera[3:]
        #     camera_list_query.append(camera)
        # camera_query = ','.join(camera_list_query)

        cameras = []
        for x in range(len(camera_list)):
            camera = Camera.objects.filter(uid=camera_list[x]).first()
            # if no_prepend_cam:
            #     cameras.append("'cam{}'".format(camera_list[x]))
            # else:
            cameras.append("'{}'".format(camera.time_uid))

        #        cameras_database = 'events.cam in ' + '({})'.format(', '.join(cameras))

        cameras_database = '{column}.cam in '.format(column=column) + '({})'.format(', '.join(cameras))
        print(cameras_database, flush=True)
        return cameras_database


class VideosGetMessage(ArchiveQueueEndpoint):
    response_topic = '/archive/video'
    response_message_type = 'archive_video'

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)

        if self.check_request_params(params):
            return

        data = params['data']
        print('params', data, flush=True)

        camera_list = data['cameras']
        camera_list_query = []
        for camera in camera_list:
            camera = Camera.objects.filter(uid=camera).first()
            if camera:
                camera_list_query.append(camera.time_uid)

        camera_query = ','.join(camera_list_query)

        startTs = int(data['start_timestamp']) if int(data['start_timestamp']) % 600 == 0 else int(
            data['start_timestamp']) - 600
        endTs = int(data['stop_timestamp']) if int(data['stop_timestamp']) % 600 == 0 else int(
            data['stop_timestamp']) + 600

        query_params = {
            'startTs': startTs * 1000,
            'endTs': endTs * 1000,
            'cameras': camera_query,
            'skip': 0 if 'skip' not in data.keys() else data['skip'],
            'limit': 10000 if 'limit' not in data.keys() else data['limit']
        }

        print(query_params, flush=True)

        response = requests.get('http://{}:5005/archive_video'.format(self.default_serv.address), params=query_params)

        response_data = json.loads(response.content.decode())
        data = {'videos': []}
        for video in response_data:
            video_data = {
                'id': video['id'],
                'camera': video['cam'],
                'start_timestamp': video['start_posix_time'],
                'stop_timestamp': video['end_posix_time'],
                'file_size': video['fileSize'],
                'path': video['archivePostfix'],
            }
            data['videos'].append(video_data)

        self.send_data_response(data)
        return


class ArchiveEventsMessage(ArchiveQueueEndpoint):
    response_topic = '/archive/events'
    response_message_type = 'archive_events'

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)

        if self.check_request_params(params):
            return

        data = params['data']
        print('params', data, flush=True)


        camera_query = self.prepare_camera_query('events', data)

        start_timestamp = int(data['start_timestamp'])
        end_timestamp = int(data['stop_timestamp'])

        conf_low = False
        conf_medium = False
        conf_high = False

        if 'confidence_low' in data and data['confidence_low']:
            conf_low = data['confidence_low']

        if 'confidence_medium' in data and data['confidence_medium']:
            conf_medium = data['confidence_medium']

        if 'confidence_high' in data and data['confidence_high']:
            conf_high = data['confidence_high']

        if True in [conf_low, conf_medium, conf_high]:
            confidence_db = check_confidence(conf_low, conf_medium, conf_high)
        else:
            confidence_db = ''

        types_db = ''
        if 'event_types' in data:
            if not isinstance(data['event_types'], list):
                error = RequestParamValidationError('value of event_types must be instance of list')
                print(error)
                self.send_error_response(error)
            elif len(data['event_types']) == 0:
                error = RequestParamValidationError('event_types list must not be empty')
                print(error)
                self.send_error_response(error)
            else:
                types_db = ' and type in ({})'.format(data['event_types'])

        reactions_db = ''
        if 'reactions' in data:
            if not isinstance(data['reactions'], list):
                error = RequestParamValidationError('value of reactions must be instance of list')
                print(error)
                self.send_error_response(error)
            elif len(data['event_types']) == 0:
                error = RequestParamValidationError('reactions list must not be empty')
                print(error)
                self.send_error_response(error)
            else:
                reactions_db = ' and reaction in ({})'.format(reactions)

        skip_value = data['skip'] if 'skip' in data else ''
        if skip_value != '':
            skip_value = ' offset {skip_value}'.format(skip_value=skip_value)

        limit_value = data['limit'] if 'limit' in data else ''
        if limit_value != '':
            limit_value = ' limit {limit_value}'.format(limit_value=limit_value)

        db_query_str = (
                "select id,cam,archive_file1,archive_file2,start_timestamp,end_timestamp,type,confidence,reaction,date,file_offset_sec from events where {cam}"
                .format(cam=camera_query) + ' and  start_timestamp >=' + str(start_timestamp * 1000) + ' and '
                + 'end_timestamp <=' + str(end_timestamp * 1000) + confidence_db + types_db + reactions_db +
                ' order by start_timestamp desc {offset} {limit};'
                .format(offset=skip_value, limit=limit_value))

        conn = psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
        cur = conn.cursor()

        cur.execute(db_query_str)
        rows = cur.fetchall()
        conn.close()

        result = []
        for event in rows:
            result.append(
                {
                    'event_id': event[0],
                    'event_camera_id': event[1],
                    # 'archiveStartHint': event[2],
                    # 'archiveEndHint': event[3],
                    'event_start_timestamp': event[4],
                    'event_end_timestamp': event[5],
                    'event_type': event[6],
                    'event_confidence': event[7],
                    'event_reaction': event[8],
                    # 'date': event[9],
                    # 'offset': event[10]
                }
            )

        self.send_data_response(result)
        return
