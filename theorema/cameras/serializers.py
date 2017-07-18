from rest_framework import serializers
from .models import Server, Camera, CameraGroup

class ServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Server
        fields = ('id', 'name', 'address',)


class CameraGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraGroup
        fields = (
                'id', 'name'
        )

class CameraSerializer(serializers.ModelSerializer):
    group = serializers.CharField()
    class Meta:
        model = Camera
        fields = (
                'id', 'cam', 'name', 'address', 'fps', 'analysis', 'resolution',
                'storage_life', 'compress_level', 'is_active', 'port', 'group',
        )

    def to_representation(self, camera):
        res = super().to_representation(camera)
        res['group'] = CameraGroupSerializer(context=self.context).to_representation(camera.group)
        return res

    def create(self, validated_data):
        group = validated_data.pop('group')
        try:
            group_id = int(group)
        except:
            group_obj = CameraGroupSerializer().create({'name': group})
        else:
            group_obj = CameraGroup.objects.get(id=group_id)
        validated_data['group'] = group_obj
        return super().create(validated_data)

    def update(self, camera, validated_data):
        group = validated_data.pop('group')
        try:
            group_id = int(group)
        except:
            group_obj = CameraGroupSerializer().create({'name': group})
            group_obj.save()
        else:
            group_obj = CameraGroup.objects.get(id=group_id)
        validated_data['group'] = group_obj
        return super().update(camera, validated_data)
