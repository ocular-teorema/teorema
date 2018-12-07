import traceback
import sys
import requests
import json
import random
from rest_framework import serializers
from rest_framework.exceptions import APIException
from .models import Server, Camera, CameraGroup, NotificationCamera, Quadrator, Camera2Quadrator
from theorema.m2mhelper import M2MHelperSerializer
from theorema.orgs.models import OcularUser
from rest_framework.response import Response
from rest_framework import status

CAM_TYPES={1:'s', 2:'a', 3:'f'}

class ServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Server
        fields = ('id', 'name', 'address', 'type', 'organization', 'parent_server_id')

    def create(self, validated_data):
        res = super().create(validated_data)
        try:
            raw_response = requests.post('http://{}:5005'.format(validated_data['address']), timeout=5)
        except Exception as e:
            res.delete()
            raise APIException(code=400, detail={'status': 1, 'message': str(e)})
        return res


class CameraGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraGroup
        fields = (
                'id', 'name'
        )


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationCamera
        fields = ('id', 'organization', 'users', 'camera', 'camera_group', 'notify_events', 'notify_time_start',
                  'notify_time_stop', 'notify_alert_level')

    def create(self, validated_data):
       validated_data['organization']=self.context['request'].user.organization
       return super().create(validated_data) 


class CameraSerializer(M2MHelperSerializer):
    camera_group = serializers.JSONField(required=True)
    class Meta:
        model = Camera
        fields = (
                'id', 'name', 'address', 'analysis',
                'storage_life', 'compress_level', 'is_active', 'server',
                'camera_group', 'organization', 'port', 'notify_email', 
                'notify_phone', 'notify_events', 'notify_time_start',
                'notify_time_stop', 'notify_alert_level', 'notify_send_email',
                'notify_send_sms', 'indefinitely', 'archive_path'
        )
        extra_kwargs = {
            'port': {'read_only': True}
        }

    def create(self, validated_data):
#        if not OcularUser.objects.exists():
#            raise APIException(code=400, detail={'status': 1, 'message': 'user doesn"t exist'})
#        max_cams=requests.post('http://78.46.97.176:1234/account', json={'hash':OcularUser.objects.last().hardware_hash})
#        if Camera.objects.filter(analysis=validated_data['analysis']).count() == max_cams.json()['max_cams'][CAM_TYPES[validated_data['analysis']]]:
#            raise APIException(code=400, detail={'status': 1, 'message': 'no pain - no gain'})
        if isinstance(validated_data['camera_group'], int):
            validated_data['camera_group'] = CameraGroup.objects.get(id=int(validated_data['camera_group']))
            camera_group = None
        else:
            camera_group = CameraGroup(name=validated_data['camera_group'], organization=validated_data['organization'])
            camera_group.save()
            validated_data['camera_group'] = camera_group
        port = Camera.objects.last().port + 200 if Camera.objects.exists() else 15000
        validated_data['port'] = port
        res = super().create(validated_data)

        try:
            worker_data = {k:v for k,v in validated_data.items()}
            worker_data.pop('server')
            worker_data.pop('camera_group')
            worker_data.pop('organization')
            worker_data['id'] = res.id
            worker_data['notify_time_start'] = str(worker_data.get('notify_time_start', '00:00:00'))
            worker_data['notify_time_stop'] = str(worker_data.get('notify_time_stop', '00:00:00'))
            raw_response = requests.post('http://{}:5005'.format(validated_data['server'].address), json=worker_data)
            worker_response = json.loads(raw_response.content.decode())
            print('create worker_response:', worker_response, flush=True)
        except Exception as e:
            res.delete()
            if camera_group:
                camera_group.delete()
            raise APIException(code=400, detail={'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))})
        if worker_response['status']:
            res.delete()
            if camera_group:
                camera_group.delete()
            raise APIException(code=400, detail={'status': 1, 'message': worker_response['message']})
        return res

    def update(self, camera, validated_data):
        try:
            worker_data = {k:v for k,v in validated_data.items()}
            worker_data.pop('server')
            worker_data.pop('camera_group')
            worker_data.pop('organization')
            worker_data['notify_time_start'] = str(worker_data.get('notify_time_start', '00:00:00'))
            worker_data['notify_time_stop'] = str(worker_data.get('notify_time_stop', '00:00:00'))
            worker_data['id'] = camera.id
            worker_data['port'] = camera.port
            raw_response = requests.patch('http://{}:5005'.format(validated_data['server'].address), json=worker_data)
            worker_response = json.loads(raw_response.content.decode())
            print('update worker response', worker_response, flush=True)
        except Exception as e:
            raise APIException(code=400, detail={'message': str(e)})
        if worker_response['status']:
            raise APIException(code=400, detail={'message': worker_response['message']})

        if isinstance(validated_data['camera_group'], int):
            validated_data['camera_group'] = CameraGroup.objects.get(id=int(validated_data['camera_group']))
        else:
            camera_group = CameraGroup(name=validated_data['camera_group'], organization=validated_data['organization'])
            camera_group.save()
            validated_data['camera_group'] = camera_group

        return super().update(camera, validated_data)

    def to_representation(self, camera, with_group=True):
        res = super().to_representation(camera)
        if with_group:
            res['camera_group'] = CameraGroupSerializer().to_representation(camera.camera_group)
        else:
            res.pop('camera_group')
        if not self.context['request'].user.is_staff and not self.context['request'].user.is_organization_admin:
            for key in list(res.keys()):
                if key.startswith('notify'):
                    res.pop(key)
        res['ws_video_url'] = 'ws://%s/video_ws/?port=%s' % (camera.server.address, camera.port+50)
        res['rtmp_video_url'] = 'rtmp://%s:1935/vasrc/cam%s' % (camera.server.address, camera.id)
        res['m3u8_video_url'] = 'http://%s:8080/vasrc/cam%s/index.m3u8' % (camera.server.address, camera.id)
        return res

class QuadratorSerializer(serializers.ModelSerializer):
    cameras = serializers.JSONField(write_only=True)
    class Meta:
        model = Quadrator
        fields = (
                'id', 'name', 'num_cam_x', 'num_cam_y', 'output_width', 'output_height', 'output_FPS',
                'output_quality', 'port', 'organization', 'server', 'cameras'
        )
        extra_kwargs = {
            'port': {'read_only': True},
            'organization': {'read_only': True},
        }

    def create(self, validated_data):
        if not self.context['request'].user.is_staff:
            validated_data['organization'] = self.context['request'].user.organization
        cameras = validated_data.pop('cameras')
        validated_data['port'] = random.randrange(15000, 60000)
        res = super().create(validated_data)
        try:
            worker_data = {k:v for k,v in validated_data.items()}
            worker_data.pop('server')
            worker_data.pop('organization')
            worker_data['type'] = 'quad'
            worker_data['id'] = res.id
            worker_data['cameras'] = []
            for c_id in cameras:
                c = Camera.objects.get(id=c_id)
                worker_data['cameras'].append({'name': c.name, 'isPresent': True, 'port': c.id})
            raw_response = requests.post('http://{}:5005'.format(validated_data['server'].address), json=worker_data, timeout=5)
            worker_response = json.loads(raw_response.content.decode())
            print('POST worker_response:', worker_response, flush=True)
        except Exception as e:
            raise APIException(code=400, detail={'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))})
        if worker_response['status']:
            raise APIException(code=400, detail={'message': worker_response['message']})
        for cam_id in cameras:
            Camera2Quadrator(camera_id = cam_id, quadrator=res).save()
        return res

    def to_representation(self, quadrator):
        res = super().to_representation(quadrator)
        res['cameras'] = [x.camera.id for x in quadrator.camera2quadrator_set.all()]
        res['ws_video_url'] = 'ws://%s/video_ws/?port=%s' % (quadrator.server.address, quadrator.port)
        res['m3u8_video_url'] = 'http://%s:8080/vasrc/quad%s/index.m3u8' % (quadrator.server.address, quadrator.id)
        return res

    def update(self, quadrator, validated_data):
        user = self.context['request'].user
        if not user.is_admin:
            validated_data['organization'] = self.context['request'].user.organization
        cameras = validated_data.pop('cameras')
        res = super().update(quadrator, validated_data)
        try:
            worker_data = {k:v for k,v in validated_data.items()}
            worker_data.pop('server')
            worker_data.pop('organization')
            worker_data['type'] = 'quad'
            raw_response = requests.patch('http://{}:5005'.format(validated_data['server'].address), json=worker_data, timeout=5)
            worker_response = json.loads(raw_response.content.decode())
            print('PATCH worker_response:', worker_response)
        except Exception as e:
            res.delete()
            raise APIException(code=400, detail={'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))})
        if worker_response['status']:
            raise APIException(code=400, detail={'message': worker_response['message']})

        quadrator.camera2quadrator_set.all().delete()
        for cam_id in cameras:
            Camera2Quadrator(camera_id = cam_id, quadrator=res).save()
        return res
