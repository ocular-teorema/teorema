from rest_framework import serializers
from .models import Organization, OcularUser
from theorema.users.models import User
from rest_framework.exceptions import APIException
import requests
from theorema.settings import lk_url

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
            max_cam = str(validated_data['max_cam'])
            user_id = OcularUser.objects.last().remote_id
            result = requests.post('{}api/v1/cam_pay/'.format(lk_url), json={'user_id':user_id, 'cam':max_cam, "sum":234})
            z = result
            if result.json()['success_url'] != None:
                return super().update(instance, validated_data)
        except:
            raise APIException(code=400, detail={'status': 'wrong'})

    class Meta:
        model = OcularUser
        fields = ('id', 'hardware_hash', 'max_cam', 'type', 'remote_id')
      
