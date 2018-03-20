from django.http import HttpResponseForbidden
from rest_framework import serializers
from .models import User, CamSet
from rest_framework.exceptions import APIException

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
                'id', 'username', 'fio', 'password', 'is_staff', 'is_organization_admin', 
                'email', 'organization', 'cameras_access', 'phone', 'timezone'

        )
        extra_kwargs = {
            'password': {'write_only': True},
            'is_staff': {'read_only': True},
        }

    def create(self, validated_data):
#        if self.validated_data['is_organization_admin'] and User.objects.filter(organization=self.validated_data['organization'], is_organization_admin=True).count() > 1:
#            raise APIException(code=400, detail={'status': 1, 'message': 'too much'})
        return super().create(validated_data)
        


class CamSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CamSet
        fields = (
                'id', 'user', 'name', 'cameras', 'mode',
        )
        extra_kwargs = {
            'user': {'read_only': True}
        }

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

