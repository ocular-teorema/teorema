from queue_api.common import QueueEndpoint
from onvif import ONVIFCamera
import time
from queue_api.messages import RequestParamValidationError
from theorema.cameras.models import Camera


class PtzControlQueueEndpoint(QueueEndpoint):

    def move(self, x_coord, y_coord, zoom, address):
        user = address.split('@')[0].split('/')[-1].split(':')[0]
        password = address.split('@')[0].split('/')[-1].split(':')[1]
        ip = address.split('@')[1].split('/')[0].split(':')[0]
        port = address.split('@')[1].split('/')[0].split(':')[1]
        mycam = ONVIFCamera(ip, port, user, password)
        # Create media service object
        media = mycam.create_media_service()

        # Create ptz service object
        ptz = mycam.create_ptz_service()

        # Get target profile
        media_profile = media.GetProfiles()[0]

        # Get PTZ configuration options for getting continuous move range
        request = ptz.create_type('GetConfigurationOptions')
        request.ConfigurationToken = media_profile.PTZConfiguration.token
        ptz_configuration_options = ptz.GetConfigurationOptions(request)

        move_request = ptz.create_type('AbsoluteMove')
        move_request.ProfileToken = media_profile.token
        # if move_request.Velocity is None:
        move_request.Velocity = ptz.GetStatus({'ProfileToken': media_profile.token}).Position

        # Get range of pan and tilt
        # NOTE: X and Y are velocity vector
        x_max = ptz_configuration_options.Spaces.ContinuousPanTiltVelocitySpace[0].XRange.Max
        x_min = ptz_configuration_options.Spaces.ContinuousPanTiltVelocitySpace[0].XRange.Min
        y_max = ptz_configuration_options.Spaces.ContinuousPanTiltVelocitySpace[0].YRange.Max
        y_min = ptz_configuration_options.Spaces.ContinuousPanTiltVelocitySpace[0].YRange.Min

        print(x_min, x_max, y_min, y_max, flush=True)

        print('move ...')
        move_request.Velocity.PanTilt.x += x_coord
        move_request.Velocity.PanTilt.y += y_coord
        move_request.Velocity.Zoom += zoom

        # ptz.Stop({'ProfileToken': move_request.ProfileToken})

        ptz.AbsoluteMove(move_request)

        time.sleep(3)
        # Stop continuous move
        ptz.Stop({'ProfileToken': move_request.ProfileToken})



class PanControlMessage(PtzControlQueueEndpoint):
    request_required_params = [
        # 'camera_id',
        'step'
    ]
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'ptz_control'


    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        print('params', params['data'], flush=True)

        #self.response_topic = self.response_topic.format(cam_id=message['camera_id'])

        if self.check_request_params(params['data']):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                self.move(int(params['step']), 0, 0, camera.address)
            except:
                print('some error', flush=True)
                error = RequestParamValidationError('camera with id {id} can not move'.format(id=params['camera_id']))
                self.send_error_response(error)
                return
        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=params['camera_id']))
            self.send_error_response(error)
            return

        self.send_success_response()
        return {'message sent'}


class TiltControlMessage(PtzControlQueueEndpoint):
    request_required_params = [
        # 'camera_id',
        'step'
    ]
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'ptz_control'


    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        print('params', params['data'], flush=True)

        #self.response_topic = self.response_topic.format(cam_id=message['camera_id'])

        if self.check_request_params(params['data']):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                self.move(0, int(params['step']), 0, camera.address)
            except:
                print('some error', flush=True)
                error = RequestParamValidationError('camera with id {id} can not move'.format(id=params['camera_id']))
                self.send_error_response(error)
                return
        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=params['camera_id']))
            self.send_error_response(error)
            return

        self.send_success_response()
        return {'message sent'}


class ZoomControlMessage(PtzControlQueueEndpoint):
    request_required_params = [
        # 'camera_id',
        'step'
    ]
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'ptz_control'


    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        print('params', params['data'], flush=True)

        #self.response_topic = self.response_topic.format(cam_id=message['camera_id'])

        if self.check_request_params(params['data']):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                self.move(0, 0, int(params['step']), camera.address)
            except:
                print('some error', flush=True)
                error = RequestParamValidationError('camera with id {id} can not move'.format(id=params['camera_id']))
                self.send_error_response(error)
                return
        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=params['camera_id']))
            self.send_error_response(error)
            return

        self.send_success_response()
        return {'message sent'}
