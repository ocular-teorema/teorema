from django.http import HttpResponseForbidden
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
                'id', 'username', 'fio', 'password', 'is_staff', 'is_organization_admin', 
                'email', 'organization', 
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'is_staff': {'read_only': True},
        }

