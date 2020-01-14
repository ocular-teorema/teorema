from queue_api.common import QueueEndpoint
import time
from queue_api.messages import RequestParamValidationError
from theorema.cameras.models import Camera
import zeep
from onvif import ONVIFCamera, ONVIFService
import datetime

def zeep_pythonvalue(self, xmlvalue):
    return xmlvalue


def address_parse(address):
    if '@' in address:
        user = address.split('@')[0].split('/')[-1].split(':')[0]
        password = address.split('@')[0].split('/')[-1].split(':')[1]
        ip = address.split('@')[1].split('/')[0].split(':')[0]
        try:
            port = address.split('@')[1].split('/')[0].split(':')[1]
        except:
            port = 80
    else:
        ip = address.split('/')[2].split(':')[0]
        try:
            port = address.split('/')[2].split(':')[1]
        except:
            port = 80
        port = 8899
        user = address.split('/')[-1].split('&')[0].split('=')[-1]
        password = address.split('/')[-1].split('&')[1].split('=')[-1]

    return ip, port, user, password


class PtzControlQueueEndpoint(QueueEndpoint):
    def camera_initialization(self, address):
        print('address', address, flush=True)
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

        return ptz, media_profile


class AbsoluteMoveMessage(PtzControlQueueEndpoint):
    request_required_params = [
        'pan',
        'tilt',
        'zoom'
    ]
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_absolute_move'

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        print('params', params['data'], flush=True)

        if self.check_request_params(params['data']['position']):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(address=camera.address)

                move_request = ptz.create_type('AbsoluteMove')
                move_request.ProfileToken = media_profile.token
                move_request.Position = ptz.GetStatus({'ProfileToken': media_profile.token}).Position
                move_request.Speed = media_profile.PTZConfiguration.DefaultPTZSpeed

                print('current position', move_request, flush=True)

                move_request.Position.PanTilt.x = params['data']['position']['pan']
                move_request.Position.PanTilt.y = params['data']['position']['tilt']
                move_request.Position.Zoom.x = params['data']['position']['zoom']
                if 'speed' in params['data']:
                    if params['data']['speed'] is not None:
                        move_request.Speed.PanTilt.x = params['data']['speed']['pan']
                        move_request.Speed.PanTilt.y = params['data']['speed']['tilt']
                        move_request.Speed.Zoom.x = params['data']['speed']['zoom']

                print('move request', move_request, flush=True)

                ptz.AbsoluteMove(move_request)
                time.sleep(3)
                ptz.Stop({'ProfileToken': move_request.ProfileToken})

                move_request.Position = ptz.GetStatus({'ProfileToken': media_profile.token}).Position
                print('new position', move_request, flush=True)


                position = {
                    'pan': move_request.Position.PanTilt.x,
                    'tilt': move_request.Position.PanTilt.y,
                    'zoom': move_request.Position.Zoom.x
                }

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

class ContinuousMoveMessage(PtzControlQueueEndpoint):
    request_required_params = [
        'pan',
        'tilt',
        'zoom'
    ]
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_continuous_move'

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        print('params', params['data'], flush=True)

        if self.check_request_params(params['data']['speed']):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(address=camera.address)

                move_request = ptz.create_type('ContinuousMove')
                move_request.ProfileToken = media_profile.token
                move_request.Velocity = media_profile.PTZConfiguration.DefaultPTZSpeed

                print('current position', move_request, flush=True)

                move_request.Velocity.PanTilt.x = params['data']['speed']['pan']
                move_request.Velocity.PanTilt.y = params['data']['speed']['tilt']
                move_request.Velocity.Zoom.x = params['data']['speed']['zoom']
                if 'timeout' in params['data']:
                    if params['data']['timeout'] is not None:
                        move_request.Timeout = datetime.timedelta(0, int(params['data']['timeout']))

                print('move request', move_request, flush=True)

                ptz.ContinuousMove(move_request)

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

        self.send_success_response()
        return {'message sent'}

class RelativeMoveMessage(PtzControlQueueEndpoint):
    request_required_params = [
        'pan',
        'tilt',
        'zoom'
    ]
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_relative_move'

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        print('params', params['data'], flush=True)

        if self.check_request_params(params['data']['position']):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(address=camera.address)

                move_request = ptz.create_type('AbsoluteMove')
                move_request.ProfileToken = media_profile.token
                move_request.Position = ptz.GetStatus({'ProfileToken': media_profile.token}).Position

                print('current position', move_request, flush=True)

                if (move_request.Position.PanTilt.x + params['data']['position']['pan']) % 2 > 1:
                    move_request.Position.PanTilt.x = (move_request.Position.PanTilt.x + params['data']['position']['pan']) % 2 - 2
                else:
                    move_request.Position.PanTilt.x = (move_request.Position.PanTilt.x + params['data']['position']['pan']) % 2

                if (move_request.Position.PanTilt.y + params['data']['position']['tilt']) >= 1:
                    move_request.Position.PanTilt.y = 0.99
                elif (move_request.Position.PanTilt.y + params['data']['position']['tilt']) <= -1:
                    move_request.Position.PanTilt.y = -0.99
                else:
                    move_request.Position.PanTilt.y += params['data']['position']['tilt']

                if (move_request.Position.Zoom.x + params['data']['position']['zoom']) >= 1:
                    move_request.Position.Zoom.x = 0.99
                elif (move_request.Position.Zoom.x + params['data']['position']['zoom']) <= 0:
                    move_request.Position.Zoom.x = 0.01
                else:
                    move_request.Position.Zoom.x += params['data']['position']['zoom']

                if 'speed' in params['data']:
                    if params['data']['speed'] is not None:
                        move_request.Speed.PanTilt.x = params['data']['speed']['pan']
                        move_request.Speed.PanTilt.y = params['data']['speed']['tilt']
                        move_request.Speed.Zoom.x = params['data']['speed']['zoom']

                print('move request', move_request, flush=True)

                ptz.AbsoluteMove(move_request)
                time.sleep(3)
                ptz.Stop({'ProfileToken': move_request.ProfileToken})

                move_request.Position = ptz.GetStatus({'ProfileToken': media_profile.token}).Position
                print('new position', move_request, flush=True)

                position = {
                    'pan': move_request.Position.PanTilt.x,
                    'tilt': move_request.Position.PanTilt.y,
                    'zoom': move_request.Position.Zoom.x
                }

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

class StopMoveMessage(PtzControlQueueEndpoint):
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_stop_move'

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        print('params', params['data'], flush=True)

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(address=camera.address)

                ptz.Stop({'ProfileToken': media_profile.token})

                stop_position = ptz.GetStatus({'ProfileToken': media_profile.token}).Position
                print('stop position', stop_position, flush=True)

                position = {
                    'pan': stop_position.PanTilt.x,
                    'tilt': stop_position.PanTilt.y,
                    'zoom': stop_position.Zoom.x
                }

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

