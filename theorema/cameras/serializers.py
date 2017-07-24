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
    class Meta:
        model = Camera
        fields = (
                'id', 'cam', 'name', 'address', 'fps', 'analysis', 'resolution',
                'storage_life', 'compress_level', 'is_active', 'port', 'server',
        )
