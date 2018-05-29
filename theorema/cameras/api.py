import requests
import json
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import APIException
from .models import Server, Camera, CameraGroup, NotificationCamera
from .serializers import ServerSerializer, CameraSerializer,CameraGroupSerializer, NotificationSerializer
from theorema.other.cache_fix import CacheFixViewSet
from theorema.permissions import ReadOnly
from theorema.users.models import CamSet
from rest_framework.decorators import api_view
from rest_framework.response import Response
from theorema.orgs.models import *
import hashlib 

class NotificationViewSet(CacheFixViewSet):
    queryset = NotificationCamera.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        if not self.request.user.is_staff:
            return self.queryset.filter(organization=self.request.user.organization)
        return self.queryset

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


@api_view(['POST'])
def add_cams(request):
    print(request)
    print(request.data)
    add_cams = []
    hash = request.data['code']
#    return Response({'sdasd':request.data})
    hash_list = hash.split('-')
    user = OcularUser.objects.filter().last()
    user_hash = user.hardware_hash
#    return Response({hashlib.sha224(str.encode(user_hash)).hexdigest(): hash_list[0]})
#    m = rsa.decrypt(n, priv_key)
#    return Response({'c':n})
    
#        user = OcularUser.objects.filter().last()
#        user_hash = user.hardware_hash
#        return Response({hashlib.sha224(str.encode(user_hash)).hexdigest(): 1})
    if hashlib.sha224(str.encode(user_hash)).hexdigest() ==  hash_list[0]:
#        return Response({'hash' : 'ok'})
        for el in hash_list[1:4]:
            for e in range(100):
                e = str(e)+'abc'
                if hashlib.sha224(str.encode(e)).hexdigest() == el:
                    add_cams.append(e[:-3])
        user.max_cam = {"a":add_cams[0], "f":add_cams[1], "s":add_cams[2] }
        user.save()
        return Response({'staus':'ok'})                
    else:
        pass
#    code = bytes(request.data['code'], encoding='utf-8')
#    m = rsa.decrypt(code, bob_priv)
#    u = m.decode('utf-8')
      
#    if str(request.data['code']) == '123':
    return Response({'status':'none'})
