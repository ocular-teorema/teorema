from rest_framework import serializers
from .models import Organization
from theorema.users.models import User

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('id', 'name')

    def create(self, validated_data):
        result = super().create(validated_data)
        User.objects.create(
            username='super_{}'.format(result.name),
            password='pass_{}'.format(result.name),
            organization_id=result.id,
            is_organization_admin=True,
            fio=''
        )
        return result

