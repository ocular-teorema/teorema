from queue_api.common import QueueEndpoint
import time
from queue_api.messages import RequestParamValidationError
from theorema.cameras.models import Camera
import zeep
from onvif import ONVIFCamera, ONVIFService
import datetime
import re


def zeep_pythonvalue(self, xmlvalue):
    return xmlvalue


def address_parse(camera):
    address = camera.address
    ip = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', address)[0]
    port = camera.onvif_port

    if camera.onvif_username:
        user = camera.onvif_username
    else:
        if '@' in address:
            user = address.split('@')[0].split('/')[-1].split(':')[0]
        else:
            user = re.findall(r'user=(.*?)&', address)[0]

    if camera.onvif_password:
        password = camera.onvif_password
    else:
        if '@' in address:
            password = address.split('@')[0].split('/')[-1].split(':')[1]
        else:
            password = re.findall(r'password=(.*?)&', address)[0]

    return ip, port, user, password


class PtzControlQueueEndpoint(QueueEndpoint):
    def camera_initialization(self, camera):
        print('address', camera.address, flush=True)

        cam_profile = getattr(self, 'cam' + str(camera.id), None)
        if not cam_profile:
            zeep.xsd.simple.AnySimpleType.pythonvalue = zeep_pythonvalue

            mycam = ONVIFCamera(*address_parse(camera), no_cache=True)

            # Create media service object
            media = mycam.create_media_service()

            # Create ptz service object
            ptz = mycam.create_ptz_service()

            # Get target profile
            media_profile = media.GetProfiles()[0]
            setattr(self, 'cam' + str(camera.id), {'ptz': ptz, 'media_profile': media_profile})

            return ptz, media_profile
        else:
            print('configuration already exist', flush=True)
            return cam_profile['ptz'], cam_profile['media_profile']


class AbsoluteMoveMessage(PtzControlQueueEndpoint):
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_absolute_move'

    schema = {
        "type": "object",
        "properties": {
            "camera_id": {"type": "string"},
            "data": {
                "type": "object",
                "properties": {
                    "position": {
                        "type": "object",
                        "properties": {
                            "pan": {"type": "number"},
                            "tilt": {"type": "number"},
                            "zoom": {"type": "number"}
                        },
                        "required": ["pan", "tilt", "zoom"]
                    },
                    "speed": {
                        "type": "object",
                        "properties": {
                            "pan": {"type": "number"},
                            "tilt": {"type": "number"},
                            "zoom": {"type": "number"}
                        },
                        "required": ["pan", "tilt", "zoom"]
                    }
                },
                "required": ["position"]
            }
        },
        "required": ["camera_id", "data"]
    }

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        self.try_log_params(params['data'])

        if self.check_request_params(params):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(camera)

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

                move_request.Position.PanTilt.space = \
                    ptz.GetCompatibleConfigurations({'ProfileToken': media_profile.token})[0][
                        'DefaultAbsolutePantTiltPositionSpace']
                move_request.Position.Zoom.space = \
                    ptz.GetCompatibleConfigurations({'ProfileToken': media_profile.token})[0][
                        'DefaultAbsoluteZoomPositionSpace']

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
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_continuous_move'

    schema = {
        "type": "object",
        "properties": {
            "camera_id": {"type": "string"},
            "data": {
                "type": "object",
                "properties": {
                    "speed": {
                        "type": "object",
                        "properties": {
                            "pan": {"type": "number"},
                            "tilt": {"type": "number"},
                            "zoom": {"type": "number"}
                        },
                        "required": ["pan", "tilt", "zoom"]
                    },
                    "timeout": {"type": "number"}
                },
                "required": ["speed"]
            }
        },
        "required": ["camera_id", "data"]
    }

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        self.try_log_params(params['data'])

        if self.check_request_params(params):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(camera)

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

                # try:
                #     ptz.ContinuousMove(move_request)
                # except zeep.exceptions.Fault:
                move_request.Velocity.PanTilt.space = \
                    ptz.GetCompatibleConfigurations({'ProfileToken': media_profile.token})[0][
                        'DefaultContinuousPanTiltVelocitySpace']
                move_request.Velocity.Zoom.space = \
                    ptz.GetCompatibleConfigurations({'ProfileToken': media_profile.token})[0][
                        'DefaultContinuousZoomVelocitySpace']

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
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_relative_move'

    schema = {
        "type": "object",
        "properties": {
            "camera_id": {"type": "string"},
            "data": {
                "type": "object",
                "properties": {
                    "position": {
                        "type": "object",
                        "properties": {
                            "pan": {"type": "number"},
                            "tilt": {"type": "number"},
                            "zoom": {"type": "number"}
                        },
                        "required": ["pan", "tilt", "zoom"]
                    },
                    "speed": {
                        "type": "object",
                        "properties": {
                            "pan": {"type": "number"},
                            "tilt": {"type": "number"},
                            "zoom": {"type": "number"}
                        },
                        "required": ["pan", "tilt", "zoom"]
                    }
                },
                "required": ["position"]
            }
        },
        "required": ["camera_id", "data"]
    }

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        self.try_log_params(params['data'])

        if self.check_request_params(params):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(camera)

                move_request = ptz.create_type('AbsoluteMove')
                move_request.ProfileToken = media_profile.token
                move_request.Position = ptz.GetStatus({'ProfileToken': media_profile.token}).Position
                move_request.Speed = media_profile.PTZConfiguration.DefaultPTZSpeed

                print('current position', move_request, flush=True)

                if (move_request.Position.PanTilt.x + params['data']['position']['pan']) % 2 > 1:
                    move_request.Position.PanTilt.x = (move_request.Position.PanTilt.x + params['data']['position'][
                        'pan']) % 2 - 2
                else:
                    move_request.Position.PanTilt.x = (move_request.Position.PanTilt.x + params['data']['position'][
                        'pan']) % 2

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

                # try:
                #     ptz.AbsoluteMove(move_request)
                # except zeep.exceptions.Fault:
                move_request.Position.PanTilt.space = \
                ptz.GetCompatibleConfigurations({'ProfileToken': media_profile.token})[0][
                    'DefaultAbsolutePantTiltPositionSpace']
                move_request.Position.Zoom.space = \
                ptz.GetCompatibleConfigurations({'ProfileToken': media_profile.token})[0][
                    'DefaultAbsoluteZoomPositionSpace']

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

    schema = {
        "type": "object",
        "properties": {
            "camera_id": {"type": "string"},
            "data": {"type": "object"}
        },
        "required": ["camera_id", "data"]
    }

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        self.try_log_params(params['data'])

        if self.check_request_params(params):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(camera)

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


class SetHomeMessage(PtzControlQueueEndpoint):
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_set_home'

    schema = {
        "type": "object",
        "properties": {
            "camera_id": {"type": "string"},
            "data": {"type": "object"}
        },
        "required": ["camera_id", "data"]
    }

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        self.try_log_params(params['data'])

        if self.check_request_params(params):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(camera)

                ptz.SetHomePosition({'ProfileToken': media_profile.token})

            except Exception as e:
                print('some error', flush=True)
                print('Exception on camera:', e, flush=True)
                error = RequestParamValidationError('camera with id {id} can not set home position, cause: {exception}'
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


class SetPresetMessage(PtzControlQueueEndpoint):
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_set_preset'

    schema = {
        "type": "object",
        "properties": {
            "camera_id": {"type": "string"},
            "data": {
                "type": "object",
                "properties": {
                    "preset_name": {"type": "string"},
                    "preset_token": {"type": "number"}
                },
            }
        },
        "required": ["camera_id", "data"]
    }

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        self.try_log_params(params['data'])

        if self.check_request_params(params):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(camera)

                set_preset_request = ptz.create_type('SetPreset')
                set_preset_request.ProfileToken = media_profile.token
                set_preset_request.PresetName = params['data']['preset_name'] if 'preset_name' in params[
                    'data'] else None
                set_preset_request.PresetToken = params['data']['preset_token'] if 'preset_token' in params[
                    'data'] else None

                preset_response = ptz.SetPreset(set_preset_request)

                message = {'preset_token': preset_response}


            except Exception as e:
                print('some error', flush=True)
                print('Exception on camera:', e, flush=True)
                error = RequestParamValidationError('camera with id {id} can not set preset, cause: {exception}'
                                                    .format(id=params['camera_id'], exception=e)
                                                    )
                self.send_error_response(error)
                return
        else:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=params['camera_id']))
            self.send_error_response(error)
            return

        self.send_data_response(message)
        return {'message sent'}


class GotoHomeMessage(PtzControlQueueEndpoint):
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_goto_home'

    schema = {
        "type": "object",
        "properties": {
            "camera_id": {"type": "string"},
            "data": {
                "type": "object",
                "properties": {
                    "speed": {
                        "type": "object",
                        "properties": {
                            "pan": {"type": "number"},
                            "tilt": {"type": "number"},
                            "zoom": {"type": "number"}
                        },
                        "required": ["pan", "tilt", "zoom"]
                    }
                },
            }
        },
        "required": ["camera_id", "data"]
    }

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        self.try_log_params(params['data'])

        if self.check_request_params(params):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(camera)

                move_request = ptz.create_type('GotoHomePosition')
                move_request.ProfileToken = media_profile.token
                move_request.Speed = media_profile.PTZConfiguration.DefaultPTZSpeed

                if 'speed' in params['data']:
                    if params['data']['speed'] is not None:
                        move_request.Speed.PanTilt.x = params['data']['speed']['pan']
                        move_request.Speed.PanTilt.y = params['data']['speed']['tilt']
                        move_request.Speed.Zoom.x = params['data']['speed']['zoom']

                print('move request', move_request, flush=True)

                ptz.GotoHomePosition(move_request)
                time.sleep(3)
                ptz.Stop({'ProfileToken': move_request.ProfileToken})

                home_position = ptz.GetStatus({'ProfileToken': media_profile.token}).Position
                print('new position', home_position, flush=True)

                position = {
                    'pan': home_position.PanTilt.x,
                    'tilt': home_position.PanTilt.y,
                    'zoom': home_position.Zoom.x
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


class GotoPresetMessage(PtzControlQueueEndpoint):
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_goto_preset'

    schema = {
        "type": "object",
        "properties": {
            "camera_id": {"type": "string"},
            "data": {
                "type": "object",
                "properties": {
                    "speed": {
                        "type": "object",
                        "properties": {
                            "pan": {"type": "number"},
                            "tilt": {"type": "number"},
                            "zoom": {"type": "number"}
                        },
                        "required": ["pan", "tilt", "zoom"]
                    },
                    "preset_token": {"type": "number"}
                },
                "required": ["preset_token"]
            }
        },
        "required": ["camera_id", "data"]
    }

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        self.try_log_params(params['data'])

        if self.check_request_params(params):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(camera)

                move_request = ptz.create_type('GotoPreset')
                move_request.ProfileToken = media_profile.token
                move_request.PresetToken = params['data']['preset_token']
                move_request.Speed = media_profile.PTZConfiguration.DefaultPTZSpeed

                if 'speed' in params['data']:
                    if params['data']['speed'] is not None:
                        move_request.Speed.PanTilt.x = params['data']['speed']['pan']
                        move_request.Speed.PanTilt.y = params['data']['speed']['tilt']
                        move_request.Speed.Zoom.x = params['data']['speed']['zoom']

                print('move request', move_request, flush=True)

                ptz.GotoPreset(move_request)
                time.sleep(3)
                ptz.Stop({'ProfileToken': move_request.ProfileToken})

                preset_position = ptz.GetStatus({'ProfileToken': media_profile.token}).Position
                print('new position', preset_position, flush=True)

                position = {
                    'pan': preset_position.PanTilt.x,
                    'tilt': preset_position.PanTilt.y,
                    'zoom': preset_position.Zoom.x
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


class GetPresetsMessage(PtzControlQueueEndpoint):
    response_topic = '/cameras/{cam_id}/ptz_control'
    response_message_type = 'cameras_ptz_get_presets'

    schema = {
        "type": "object",
        "properties": {
            "camera_id": {"type": "string"},
            "data": {"type": "object"}
        },
        "required": ["camera_id", "data"]
    }

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']
        print('request uid', self.uuid, flush=True)
        self.try_log_params(params['data'])

        if self.check_request_params(params):
            return

        camera = Camera.objects.filter(uid=params['camera_id']).first()
        if camera:
            try:
                ptz, media_profile = self.camera_initialization(camera)

                presets_response = ptz.GetPresets({'ProfileToken': media_profile.token})

                message = []
                for preset in presets_response:
                    message.append({
                        'preset_token': preset.token,
                        'preset_name': preset.Name,
                        'preset_position': {
                            'pan': preset.PTZPosition.PanTilt.x,
                            'tilt': preset.PTZPosition.PanTilt.y,
                            'zoom': preset.PTZPosition.Zoom.x
                        } if preset.PTZPosition is not None else None
                    })

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

        self.send_data_response(message)
        return {'message sent'}
