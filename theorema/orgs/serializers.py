from rest_framework import serializers
from .models import Organization, OcularUser
from theorema.users.models import User

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
    class Meta:
        model = OcularUser
        fields = ('hardware_hash', 'max_cam')
