from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Server, Camera, CameraGroup
from .serializers import ServerSerializer, CameraSerializer, CameraGroupSerializer

class ServerViewSet(ModelViewSet):
    queryset = Server.objects.all()
    serializer_class = ServerSerializer


class CameraViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Camera.objects.all()
    serializer_class = CameraSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            return self.queryset.filter(server__organization=self.request.user.organization)
        param = self.request.query_params.get('organization', None)
        if param is not None:
            return self.queryset.filter(server__organization__id=param)
        return self.queryset
        
class CameraGroupViewSet(ModelViewSet):
    queryset = CameraGroup.objects.all()
    serializer_class = CameraGroupSerializer
