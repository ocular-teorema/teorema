import requests
import json
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import APIException
from .models import Server, Camera, CameraGroup
from .serializers import ServerSerializer, CameraSerializer, CameraGroupSerializer

class ServerViewSet(ModelViewSet):
    queryset = Server.objects.all()
    serializer_class = ServerSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            return self.queryset.filter(organization=self.request.user.organization)
        param = self.request.query_params.get('organization', None)
        if param is not None:
            return self.queryset.filter(organization__id=param)
        return self.queryset


class CameraViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Camera.objects.all()
    serializer_class = CameraSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            return self.queryset.filter(organization=self.request.user.organization)
        param = self.request.query_params.get('organization', None)
        if param is not None:
            return self.queryset.filter(organization__id=param)
        return self.queryset
    
    def destroy(self, request, pk=None):
        try:
            worker_data={'id': pk}
            camera = Camera.objects.get(id=pk)
            raw_response = requests.delete('http://{}:5000'.format(camera.server.address), json=worker_data)
            worker_response = json.loads(raw_response. content.decode())
        except Exception as e:
            raise APIException(code=400,               detail={'message': str(e)})
        if worker_response['status']:
            raise APIException(code=400,               detail={'message': worker_response['message']})
        return super().destroy(request, pk)


class CameraGroupViewSet(ModelViewSet):
    queryset = CameraGroup.objects.all()
    serializer_class = CameraGroupSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            return self.queryset.filter(organization=self.request.user.organization)
        param = self.request.query_params.get('organization', None)
        if param is not None:
            return self.queryset.filter(organization__id=param)
        return self.queryset
        
