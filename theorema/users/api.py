from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserSerializer

class UserViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            param = self.request.query_params.get('organization', None)
            if param is not None:
                return self.queryset.filter(organization__id=param)
            return self.queryset
        if self.request.user.is_organization_admin:
            return self.queryset.filter(organization=self.request.user.organization)
        return self.queryset.filter(id=self.request.user.id)


@api_view()
def profile_view(request):
    if request.user.is_anonymous:
        raise PermissionDenied()
    return Response(UserSerializer(request.user).data)
