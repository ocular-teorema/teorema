from queue_api.common import QueueEndpoint, send_in_queue
from theorema.cameras.serializers import CameraSerializer, Camera
from admin_theorema import listener


class CameraListMessages(QueueEndpoint):
    camera_group = 'default'
    organization = 'Ocular'

    def handle_request(self, params):
        print('message received', flush=True)

        name = params['name']
        address_primary = params['address_primary']
        # address_secondary = params['address_secondary']
        analysis_type = params['analysis_type']
        storage_days = params['storage_days']
        # storage_id = params['storage_id']
        # schedule_id = params['schedule_id']

        serializer_params = {
            'name': name,
            'organization': self.organization,
            'camera_group': self.camera_group,
            'address': address_primary,
            'analysis': analysis_type,
            'storage_life': storage_days

        }

        serializer = CameraSerializer(data=serializer_params)

        if serializer.is_valid():
            camera = serializer.save()
            camera.save()
        else:
            raise Exception('serializer is wrong')

        print('camera', camera, flush=True)
        return {'message sended'}

    def handle_stop_request(self, params):
        print('message received', flush=True)
        self.send_stop_response(params)
        return {'message received'}

    def handle_start_request(self, params):
        print('message received', flush=True)
        self.send_start_response(params)
        return {'message received'}

    def send_stop_response(self, params):
        print('sending message', flush=True)

        camera = Camera.objects.filter(uid=params['id']).first()
        if camera:
            data = {
                'address': camera.address,
                'analysis': camera.analysis,
                'archive_path': camera.archive_path,
                'camera_group': camera.camera_group.id,
                'compress_level': camera.compress_level,
                'id': camera.id,
                'indefinitely': camera.indefinitely,
                'is_active': False,
                'm3u8_video_url': 'http://%s:8080/vasrc/cam%s/index.m3u8' % (camera.server.address, str(camera.id)),
                'name': camera.name,
                'notify_alert_level': camera.notify_alert_level,
                'notify_email': camera.notify_email,
                'notify_events': camera.notify_events,
                'notify_phone': camera.notify_phone,
                'notify_send_email': camera.notify_send_email,
                'notify_send_sms': camera.notify_send_sms,
                'notify_time_start': camera.notify_time_start,
                'notify_time_stop': camera.notify_time_stop,
                'organization': camera.organization.id,
                'port': camera.port,
                'rtmp_video_url': 'rtmp://%s:1935/vasrc/cam%s' % (camera.server.address, str(camera.id) + camera.add_time),
                'server': camera.server.id,
                'storage_life': camera.storage_life,
                'thumb_url': 'http://%s:5005/thumb/%s/' % (camera.server.address, camera.id),
                'unique_id': str(camera.id) + camera.add_time,
                'ws_video_url': 'ws://%s/video_ws/?port=%s' % (camera.server.address, camera.port+50)
            }
            try:
                CameraSerializer().update(camera, data)
            except:
                raise Exception('fail in stopping camera')

        message = {
            'request_uid': params['request_uid'],
            'success': True
        }

        send_in_queue(self.queue, message)

    def send_start_response(self, params):
        print('sending message', flush=True)

        camera = Camera.objects.filter(uid=params['id']).first()
        if camera:
            data = {
                'address': camera.address,
                'analysis': camera.analysis,
                'archive_path': camera.archive_path,
                'camera_group': camera.camera_group,
                'compress_level': camera.compress_level,
                'id': camera.id,
                'indefinitely': camera.indefinitely,
                'is_active': True,
                'm3u8_video_url': 'http://%s:8080/vasrc/cam%s/index.m3u8' % (camera.server.address, str(camera.id)),
                'name': camera.name,
                'notify_alert_level': camera.notify_alert_level,
                'notify_email': camera.notify_email,
                'notify_events': camera.notify_events,
                'notify_phone': camera.notify_phone,
                'notify_send_email': camera.notify_send_email,
                'notify_send_sms': camera.notify_send_sms,
                'notify_time_start': camera.notify_time_start,
                'notify_time_stop': camera.notify_time_stop,
                'organization': camera.organization,
                'port': camera.port,
                'rtmp_video_url': 'rtmp://%s:1935/vasrc/cam%s' % (camera.server.address, str(camera.id) + camera.add_time),
                'server': camera.server,
                'storage_life': camera.storage_life,
                'thumb_url': 'http://%s:5005/thumb/%s/' % (camera.server.address, camera.id),
                'unique_id': str(camera.id) + camera.add_time,
                'ws_video_url': 'ws://%s/video_ws/?port=%s' % (camera.server.address, camera.port+50)
            }
            try:
                CameraSerializer().update(camera, data)
            except:
                raise Exception('fail in stopping camera')

        message = {
            'request_uid': params['request_uid'],
            'success': True
        }

        send_in_queue(self.queue, message)
