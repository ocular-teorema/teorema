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
        fields = ('id', 'name', 'address', 'type', 'organization', 'parent_server_id', 'local_address')

    def create(self, validated_data):
        res = super().create(validated_data)
        try:
            raw_response = requests.post('http://{}:5005'.format(validated_data['address']), timeout=5)
        except Exception as e:
            res.delete()
            raise APIException(code=400, detail={'status': 1, 'message': str(e)})
        return res

    def to_representation(self, server, with_group=True):
        res = super().to_representation(server)
        if not self.context['request'].user.is_staff and not self.context['request'].user.is_organization_admin:
            for key in list(res.keys()):
                if key.startswith('notify'):
                    res.pop(key)
        x_real_ip = self.context['request'].META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            ip = x_real_ip.split(',')[0]
        else:
            ip = self.context['request'].META.get('REMOTE_ADDR')

        if ip.startswith('10') or ip.startswith('192.168') or ip.startswith('172.16'):
            serv_addr = server.local_address
        else:
            serv_addr = server.address

        res["fact_address"] = serv_addr

        return res

class CameraGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraGroup
        fields = (
                'id', 'name', 'organization'
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
            camera_group_exist = CameraGroup.objects.filter(
                    name=validated_data['camera_group'],
                    organization=validated_data['organization'])
            if camera_group_exist:
                validated_data['camera_group'] = camera_group_exist.first()
                camera_group = None
            else:
                camera_group = CameraGroup(name=validated_data['camera_group'], organization=validated_data['organization'])
                camera_group.save()
                validated_data['camera_group'] = camera_group
        port = Camera.objects.last().port + 200 if Camera.objects.exists() else 15000
        validated_data['port'] = port
        # validated_data['server'] = SERVERS.index(self.context['request'].get_host()) + 1
        # validated_data['server'] = Server.objects.get(id = validated_data['server']).parent_server_id
        res = super().create(validated_data)

        try:
            represented_data = self.to_representation(res)
            worker_data = {k:v for k,v in validated_data.items()}
            worker_data['ws_video_url'] = represented_data['ws_video_url'].replace('/video_ws/?port=', ':')
            worker_data['rtmp_video_url'] = represented_data['rtmp_video_url']

            # worker_data['ws_video_url'] = 'ws://%s/video_ws/?port=%s' % (serv_addr, camera.port + 50)
            # worker_data['rtmp_video_url'] = 'rtmp://%s:1935/vasrc/cam%s' % (serv_addr, camera.id)


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
        try:
            if not self.context['request'].user.is_staff and not self.context['request'].user.is_organization_admin:
                for key in list(res.keys()):
                    if key.startswith('notify'):
                        res.pop(key)
        except:
            pass

        x_real_ip = self.context['request'].META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            ip = x_real_ip.split(',')[0]
        else:
            ip = self.context['request'].META.get('REMOTE_ADDR')

        if ip.startswith('10') or ip.startswith('192.168') or ip.startswith('172.16'):
            serv_addr = camera.server.local_address
        else:
            serv_addr = camera.server.address

        res['ws_video_url'] = 'ws://%s/video_ws/?port=%s' % (serv_addr, camera.port+50)
        res['rtmp_video_url'] = 'rtmp://%s:1935/vasrc/cam%s' % (serv_addr, camera.id)
        res['m3u8_video_url'] = 'http://%s:8080/vasrc/cam%s/index.m3u8' % (serv_addr, camera.id)
        res['thumb_url'] = 'http://%s:5005/thumb/%s/' % (serv_addr, camera.id)

        return res

class Camera2QuadratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camera2Quadrator
        fields = (
                'camera_id', 'x', 'y', 'cols', 'rows'
        )

class QuadratorSerializer(serializers.ModelSerializer):
    cameras = serializers.ListField(write_only=True)
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
            for cam in cameras:
                camera_id = cam.pop('camera_id')
                c = Camera.objects.get(id=camera_id)
                cam['camera'] = c;
                cam['quadrator'] = res;
                worker_data['cameras'].append({'name': 'cam%s' % c.id, 'posX': cam['x'] * res.output_width / res.num_cam_x, 'posY': cam['y'] * res.output_height / res.num_cam_y, 'width': cam['cols'] * res.output_width / res.num_cam_x, 'height': cam['rows'] * res.output_height / res.num_cam_y, 'port': c.id})
            print('worker_data cameras:', worker_data['cameras']);
            raw_response = requests.post('http://{}:5005'.format(validated_data['server'].address), json=worker_data, timeout=5)
            worker_response = json.loads(raw_response.content.decode())
            print('POST worker_response:', worker_response, flush=True)
        except Exception as e:
            raise APIException(code=400, detail={'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))})
        if worker_response['status']:
            raise APIException(code=400, detail={'message': worker_response['message']})
        for cam in cameras:
            Camera2Quadrator(**cam).save()
        return res


    def to_representation(self, quadrator):

        x_real_ip = self.context['request'].META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            ip = x_real_ip.split(',')[0]
        else:
            ip = self.context['request'].META.get('REMOTE_ADDR')

        if ip.startswith('10') or ip.startswith('192.168') or ip.startswith('172.16'):
            serv_addr = quadrator.server.local_address
        else:
            serv_addr = quadrator.server.address
        res = super().to_representation(quadrator)

        res['cameras'] = [Camera2QuadratorSerializer().to_representation(x) for x in quadrator.camera2quadrator_set.all()]
        res['ws_video_url'] = 'ws://%s/video_ws/?port=%s' % (serv_addr, quadrator.port)
        res['m3u8_video_url'] = 'http://%s:8080/vasrc/quad%s/index.m3u8' % (serv_addr, quadrator.id)
        return res

    def update(self, quadrator, validated_data):
        user = self.context['request'].user
        if not user.is_staff:
            validated_data['organization'] = self.context['request'].user.organization
        cameras = validated_data.pop('cameras')
        print(cameras, flush=True)
        res = super().update(quadrator, validated_data)
        try:
            worker_data = {k:v for k,v in validated_data.items()}
            worker_data.pop('server')
            worker_data.pop('organization')
            worker_data['type'] = 'quad'
            worker_data['id'] = quadrator.id
            worker_data['cameras'] = []
            for cam in cameras:
                camera_id = cam.pop('camera_id')
                c = Camera.objects.get(id=camera_id)
                cam['camera'] = c;
                cam['quadrator'] = res;
                worker_data['cameras'].append({'name': 'cam%s' % c.id, 'posX': cam['x'] * res.output_width / res.num_cam_x, 'posY': cam['y'] * res.output_height / res.num_cam_y, 'width': cam['cols'] * res.output_width / res.num_cam_x, 'height': cam['rows'] * res.output_height / res.num_cam_y, 'port': c.id})
            print('worker_data cameras:', worker_data['cameras']);
            worker_data['port'] = quadrator.port
            raw_response = requests.patch('http://{}:5005'.format(validated_data['server'].address), json=worker_data, timeout=5)
            worker_response = json.loads(raw_response.content.decode())
            print('PATCH worker_response:', worker_response)
        except Exception as e:
            raise APIException(code=400, detail={'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))})
        if worker_response['status']:
            raise APIException(code=400, detail={'message': worker_response['message']})

        quadrator.camera2quadrator_set.all().delete()
        for cam in cameras:
            Camera2Quadrator(**cam).save()
        return res
