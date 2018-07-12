from rest_framework import serializers
from .models import Organization, OcularUser
from theorema.users.models import User
from rest_framework.exceptions import APIException
import requests
class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('id', 'name')

    def create(self, validated_data):
        result = super().create(validated_data)
        u = User(
            username='super_{}'.format(result.name),
            organization_id=result.id,
            is_organization_admin=True,
            fio=''
        )
        u.password='pass_{}'.format(result.name)
        u.save()
        return result

class OcularUserSerializer(serializers.ModelSerializer):

    def update(self, instance, validated_data):
        try:
            worker_data = {k: v for k, v in validated_data.items()}
            max_cam = str(worker_data['max_cam'])
            hash = OcularUser.objects.last().hardware_hash
            result = requests.patch('http://78.46.97.176:1234/account', json={'hardware_hash':hash, 'max_cam':max_cam})
            if result.json()['status'] == 'ok':
                return super().update(instance, validated_data)
        except:
            raise APIException(code=400, detail={'status': 'wrong'})

    class Meta:
        model = OcularUser
        fields = ('id', 'hardware_hash', 'max_cam', 'type', 'remote_id')
      
