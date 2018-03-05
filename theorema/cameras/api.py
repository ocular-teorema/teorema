import requests
import json
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import APIException
from .models import Server, Camera, CameraGroup, NotificationCamera
from .serializers import ServerSerializer, CameraSerializer, NotificationSerializer, CameraGroupSerializer
from theorema.other.cache_fix import CacheFixViewSet
from theorema.permissions import ReadOnly
from theorema.users.models import CamSet

class NotificationViewSet(CacheFixViewSet):
    queryset = NotificationCamera.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated, )


class ServerViewSet(CacheFixViewSet):
    queryset = Server.objects.all()
    serializer_class = ServerSerializer
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        if not self.request.user.is_staff:
            return self.queryset.filter(organization=self.request.user.organization)
        param = self.request.query_params.get('organization', None)
        if param is not None:
            return self.queryset.filter(organization__id=param)
        return self.queryset


class CameraViewSet(CacheFixViewSet):
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
            raw_response = requests.delete('http://{}:5005'.format(camera.server.address), json=worker_data)
            worker_response = json.loads(raw_response. content.decode())

            if len(Camera.objects.filter(camera_group_id=camera.camera_group_id)) == 1:
                CameraGroup.objects.get(id=camera.camera_group_id).delete()

            for camset in CamSet.objects.all():
                if camera.id in camset.cameras:
                    camset.cameras.remove(camera.id)
                    camset.save()
                    
        except Exception as e:
            raise APIException(code=400,               detail={'message': str(e)})
        if worker_response['status']:
            raise APIException(code=400,               detail={'message': worker_response['message']})
        return super().destroy(request, pk)


class CameraGroupViewSet(CacheFixViewSet):
    queryset = CameraGroup.objects.all()
    serializer_class = CameraGroupSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            return self.queryset.filter(organization=self.request.user.organization)
        param = self.request.query_params.get('organization', None)
        if param is not None:
            return self.queryset.filter(organization__id=param)
        return self.queryset