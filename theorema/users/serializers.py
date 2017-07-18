from django.http import HttpResponseForbidden
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
                'id', 'username', 'fio', 'password', 'is_staff', 'is_chief_guard',
                'tab_security', 'tab_records', 'tab_settings', 'tab_cameras', 'email',
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'is_staff': {'read_only': True},
        }

