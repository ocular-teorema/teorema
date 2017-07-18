from rest_framework.viewsets import ModelViewSet
from .models import Server, Camera, CameraGroup
from .serializers import ServerSerializer, CameraSerializer, CameraGroupSerializer

class ServerViewSet(ModelViewSet):
    queryset = Server.objects.all()
    serializer_class = ServerSerializer


class CameraViewSet(ModelViewSet):
    queryset = Camera.objects.all()
    serializer_class = CameraSerializer


class CameraGroupViewSet(ModelViewSet):
    queryset = CameraGroup.objects.all()
    serializer_class = CameraGroupSerializer
