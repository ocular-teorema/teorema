from queue_api.common import QueueEndpoint
from onvif import ONVIFCamera
import time
from queue_api.messages import RequestParamValidationError, RequiredParamError


class PtzControlQueueEndpoint(QueueEndpoint):

    def __init__(self, exchange, server_name, topic_object=None):
        super().__init__(exchange=exchange, server_name=server_name, topic_object=topic_object)


    def move(self, x_coord, y_coord, zoom):
        mycam = ONVIFCamera(IP, PORT, USER, PASS)
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
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params['data'], flush=True)

        self.response_topic = self.response_topic.format(cam_id=self.topic_object)

        if self.check_request_params(params['data']):
            return

        try:
            self.move(int(params['step']), 0, 0)
        except:
            print('some error', flush=True)
            error = RequestParamValidationError('camera with id {id} can not move'.format(id=self.topic_object))
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
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params['data'], flush=True)

        self.response_topic = self.response_topic.format(cam_id=self.topic_object)

        if self.check_request_params(params['data']):
            return

        try:
            self.move(0, int(params['step']), 0)
        except:
            print('some error', flush=True)
            error = RequestParamValidationError('camera with id {id} can not move'.format(id=self.topic_object))
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
        self.request_uid = params['request_uid']
        print('request uid', self.request_uid, flush=True)
        print('params', params['data'], flush=True)

        self.response_topic = self.response_topic.format(cam_id=self.topic_object)

        if self.check_request_params(params['data']):
            return

        try:
            self.move(0, 0, int(params['step']))
        except:
            print('some error', flush=True)
            error = RequestParamValidationError('camera with id {id} can not move'.format(id=self.topic_object))
            self.send_error_response(error)
            return

        self.send_success_response()
        return {'message sent'}
