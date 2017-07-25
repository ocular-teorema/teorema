from rest_framework import serializers
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
    camera_group = serializers.CharField(required=False)
    class Meta:
        model = Camera
        fields = (
                'id', 'name', 'address', 'fps', 'analysis', 'resolution',
                'storage_life', 'compress_level', 'is_active', 'server',
                'camera_group', 'organization',
        )

    def create(self, validated_data):
        if isinstance(validated_data['camera_group'], int):
            validated_data['camera_group'] = CameraGroup.objects.get(id=int(validated_data['camera_group']))
        else:
            camera_group = CameraGroup(name=validated_data['camera_group'])
            camera_group.save()
            validated_data['camera_group'] = camera_group
        return super().create(validated_data)

    def update(self, camera, validated_data):
        if isinstance(validated_data['camera_group'], int):
            validated_data['camera_group'] = CameraGroup.objects.get(id=int(validated_data['camera_group']))
        else:
            camera_group = CameraGroup(name=validated_data['camera_group'])
            camera_group.save()
            validated_data['camera_group'] = camera_group
        return super().update(camera, validated_data)

    def to_representation(self, camera):
        res = super().to_representation(camera)
        res['camera_group'] = camera.camera_group.id
        return res
