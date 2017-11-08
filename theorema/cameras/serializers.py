import traceback
import sys
import requests
import json
import random
from rest_framework import serializers
from rest_framework.exceptions import APIException
from .models import Server, Camera, CameraGroup
from theorema.m2mhelper import M2MHelperSerializer

class ServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Server
        fields = ('id', 'name', 'address', 'organization')


class CameraGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraGroup
        fields = (
                'id', 'name'
        )

class CameraSerializer(M2MHelperSerializer):
    camera_group = serializers.JSONField(required=False)
    class Meta:
        model = Camera
        fields = (
                'id', 'name', 'address', 'fps', 'analysis', 'resolution',
                'storage_life', 'compress_level', 'is_active', 'server',
                'camera_group', 'organization', 'port', 'notify_email', 
                'notify_phone', 'notify_events', 'notify_time_start',
                'notify_time_stop', 'notify_alert_level', 'notify_send_email',
                'notify_send_sms',
        )
        extra_kwargs = {
            'port': {'read_only': True}
        }

    def create(self, validated_data):
        if isinstance(validated_data['camera_group'], int):
            validated_data['camera_group'] = CameraGroup.objects.get(id=int(validated_data['camera_group']))
        else:
            camera_group = CameraGroup(name=validated_data['camera_group'], organization=validated_data['organization'])
            camera_group.save()
            validated_data['camera_group'] = camera_group
        # TODO check if port already used
        validated_data['port'] = random.randrange(15000, 16000)
        result = super().create(validated_data)

        try:
            worker_data = {k:v for k,v in validated_data.items()}
            worker_data.pop('server')
            worker_data.pop('camera_group')
            worker_data.pop('organization')
            worker_data['id'] = result.id
            worker_data['notify_time_start'] = str(worker_data.get('notify_time_start', '00:00:00'))
            worker_data['notify_time_stop'] = str(worker_data.get('notify_time_stop', '00:00:00'))
            raw_response = requests.post('http://{}:5005'.format(validated_data['server'].address), json=worker_data)
            worker_response = json.loads(raw_response.content.decode())
            print('create worker_response:', worker_response)
        except Exception as e:
            result.delete()
            raise APIException(code=400, detail={'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))})
        if worker_response['status']:
            result.delete()
            raise APIException(code=400, detail={'status': 1, 'message': worker_response['message']})
        return result

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
        return res
