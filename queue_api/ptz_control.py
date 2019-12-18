from queue_api.common import QueueEndpoint
from onvif import ONVIFCamera
import time
from queue_api.messages import RequestParamValidationError
from theorema.cameras.models import Camera
import zeep
from onvif import ONVIFCamera, ONVIFService

def zeep_pythonvalue(self, xmlvalue):
    return xmlvalue


def address_parse(address):
    if '@' in address:
        user = address.split('@')[0].split('/')[-1].split(':')[0]
        password = address.split('@')[0].split('/')[-1].split(':')[1]
        ip = address.split('@')[1].split('/')[0].split(':')[0]
        try:
            port = address.split('@')[1].split('/')[0].split(':')[1]
            # mycam = ONVIFCamera(ip, port, user, password)
        except:
            port = 80
    else:
        ip = address.split('/')[2].split(':')[0]
        try:
            port = address.split('/')[2].split(':')[1]
        except:
            port = 80
        user = address.split('/')[-1].split('&')[0].split('=')[-1]
        password = address.split('/')[-1].split('&')[1].split('=')[-1]
    if password == '':
        password = user

    return ip, port, user, password


class PtzControlQueueEndpoint(QueueEndpoint):

    def move(self, x_coord, y_coord, zoom, address):
        print(address, flush=True)
        zeep.xsd.simple.AnySimpleType.pythonvalue = zeep_pythonvalue

        mycam = ONVIFCamera(*address_parse(address), no_cache=True)

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
        # print(ptz_configuration_options, flush=True)
        move_request = ptz.create_type('AbsoluteMove')
        move_request.ProfileToken = media_profile.token
        # if move_request.Velocity is None:
        move_request.Position = ptz.GetStatus({'ProfileToken': media_profile.token}).Position
        print('current position', move_request.Position, flush=True)


        print(ptz_configuration_options, flush=True)

        print('move ...', flush=True)


        if (move_request.Position.PanTilt.x + x_coord) % 2 > 1:
            move_request.Position.PanTilt.x = (move_request.Position.PanTilt.x + x_coord) % 2 - 2
        else:
            move_request.Position.PanTilt.x = (move_request.Position.PanTilt.x + x_coord) % 2
        # else:
        #     move_request.Position.PanTilt.x += x_coord

        if (move_request.Position.PanTilt.y + y_coord) >= 1:
            move_request.Position.PanTilt.y = 0.99
        elif (move_request.Position.PanTilt.y + y_coord) <= -1:
            move_request.Position.PanTilt.y = -0.99
        else:
            move_request.Position.PanTilt.y += y_coord

        if (move_request.Position.Zoom.x + zoom) >= 1:
            move_request.Position.Zoom.x = 0.99
        elif (move_request.Position.Zoom.x + zoom) <= 0:
            move_request.Position.Zoom.x = 0.01
        else:
            move_request.Position.Zoom.x += zoom


        print('move_request', move_request, type(move_request), flush=True)


        ptz.AbsoluteMove(move_request)

        time.sleep(3)
        ptz.Stop({'ProfileToken': move_request.ProfileToken})
        move_request.Position = ptz.GetStatus({'ProfileToken': media_profile.token}).Position
        print('new position', move_request.Position, flush=True)

        response_position = {
            'pan': move_request.Position.PanTilt.x,
            'tilt': move_request.Position.PanTilt.y,
            'zoom': move_request.Position.Zoom.x
        }

        return response_position




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
                position = self.move(float(params['data']['step']), 0, 0, camera.address)
            except Exception as e:
                print('some error', flush=True)
                print('Exception on camera:', e, flush=True)
                error = RequestParamValidationError('camera with id {id} can not move, cause: {exception}'
                                                    .format(id=params['camera_id'], exception=e)
                                                    )
                self.send_error_response(error)
                return
        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=params['camera_id']))
            self.send_error_response(error)
            return

        self.send_data_response(position)
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
                position = self.move(0, float(params['data']['step']), 0, camera.address)
            except Exception as e:
                print('some error', flush=True)
                print('Exception on camera:', e, flush=True)
                error = RequestParamValidationError('camera with id {id} can not move, cause: {exception}'
                                                    .format(id=params['camera_id'], exception=e)
                                                    )
                self.send_error_response(error)
                return
        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=params['camera_id']))
            self.send_error_response(error)
            return

        self.send_data_response(position)
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
                position = self.move(0, 0, float(params['data']['step']), camera.address)
            except Exception as e:
                print('some error', flush=True)
                print('Exception on camera:', e, flush=True)
                error = RequestParamValidationError('camera with id {id} can not move, cause: {exception}'
                                                    .format(id=params['camera_id'], exception=e)
                                                    )
                self.send_error_response(error)
                return
        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=params['camera_id']))
            self.send_error_response(error)
            return

        self.send_data_response(position)
        return {'message sent'}
