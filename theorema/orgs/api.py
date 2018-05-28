
from rest_framework.viewsets import ModelViewSet
from .models import Organization, OcularUser
from .serializers import OrganizationSerializer, OcularUserSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
import subprocess
import hashlib
import requests
from rest_framework import status
from rest_framework.exceptions import APIException
import string
import random
from theorema.users.models import DayLeft
from django.utils import timezone
import datetime

class OrganizationViewSet(ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

class OcularUserViewSet(ModelViewSet):
    queryset = OcularUser.objects.all()
    serializer_class = OcularUserSerializer
    
    def get_queryset(self):
        return OcularUser.objects.all()


@api_view(['GET'])
def update_ocularuser_info(request): 
    if not OcularUser.objects.exists():
        md5hash = hashlib.md5()
        byte_str=bytes(str(subprocess.check_output('lspci', shell=True)), encoding='utf=8')
        md5hash.update(byte_str)
        hash = md5hash.hexdigest()
        response = requests.post('http://78.46.97.176:1234/account', json={'hash':hash, 'new_user': 'true'})
        if response.json()['status'] == 'ok':
            print(response.json())
            OcularUser.objects.create(hardware_hash=hash, max_cam=response.json()['max_cams'])
            Response(response, status=status.HTTP_200_OK)
        else:
             raise APIException(code=400, detail={'status': 1, 'message': 'something wrong'})
    else:
        pass
    return Response({'message':'already_register'}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_today_hash(request):
    md5hash = hashlib.md5()
    byte_str = bytes(str(subprocess.check_output('lspci', shell=True)), encoding='utf=8')
    md5hash.update(byte_str)
    hash = md5hash.hexdigest()
    if hash == OcularUser.objects.filter().last().hardware_hash:
        obj = DayLeft.objects.filter(user=request.user)
        if obj:
            obj.delete()
        return Response({'hash':'yes'},status=status.HTTP_200_OK)
    else:
        obj, created = DayLeft.objects.create(user=request.user)
        if created:
            obj.stop_date = timezone.now() + datetime.timedelta(7)
            obj.save()
        return Response({'hash': 'no', 'date_end':obj.strftime('%d-%m-%Y')}, status=status.HTTP_200_OK)
