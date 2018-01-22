from rest_framework import serializers
from .models import Organization
from theorema.users.models import User


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('id', 'name')

    def create(self, validated_data):
        result = super().create(validated_data)
        if not self.context['request'].user.organization:
            user = User.objects.get(id=self.context['request'].user.id)
            user.organization = result
            user.save()
        else:
            result.delete()
        return result