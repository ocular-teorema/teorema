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


#online version
#Этот метод вызывается только один раз и служит лишь для создания экземпляра Oculauser
@api_view(['GET'])
def update_ocularuser_info(request): 
    if not OcularUser.objects.exists():
        md5hash = hashlib.md5()
        byte_str=bytes(str(subprocess.check_output('lspci', shell=True)), encoding='utf=8')
        md5hash.update(byte_str)
        hash = md5hash.hexdigest()
        user = OcularUser.objects.create(hardware_hash=hash)
        try:
            response = requests.post('https://oculars.net/', json={'hash':hash})
        except:
            return Response({"status" : "bad request"})
        if response.json()['exist'] == 'True':
            user(
                max_cam=response.json()['max_cams'],
                remote_id=response.json()["user_id"]
            )
            user.save()
            return Response({"status": "userinfo_update"}, status=status.HTTP_200_OK)
        else:
            return Response({"status": "user_not_exist"})
    else:
        pass
    return Response({'status':'already_register'}, status=status.HTTP_200_OK)


#offline_version
#Этот метод используется для оффлайн регистрации
#Вызывать его следует только тогда, когда предыдущий запрос вернул "bad_request"
@api_view(['POST'], )
def update_ocularuser_info(request):
    user_cameras = {}
    user = OcularUser.objects.filter().last()
    data = request.data["data"]
    data = data.split('-')
    if data[0] == hashlib.md5(str.encode(user.hardware_hash)).hexdigest():
        for el in data[1:4]:
            for e in range(100):
                if hashlib.md5(str.encode(str(e) + "s")).hexdigest() == el:
                    user_cameras['s'] = e
                    break
                if hashlib.md5(str.encode(str(e) + "a")).hexdigest() == el:
                    user_cameras['a'] = e
                    break
                if hashlib.md5(str.encode(str(e) + "f")).hexdigest() == el:
                    user_cameras['f'] = e
                    break
                continue
        user.max_cam = user_cameras
        return Response({"status":"update"})
    else:
        return Response({"status": "wrong_code"})



@api_view(['GET'])
def get_today_hash(request):
    md5hash = hashlib.md5()
    byte_str = bytes(str(subprocess.check_output('lspci', shell=True)), encoding='utf=8')
    md5hash.update(byte_str)
    hash = md5hash.hexdigest()
    if hash == OcularUser.objects.filter().last().hardware_hash:
        obj = DayLeft.objects.filter(user=OcularUser.objects.filter().last()).last()
        if obj:
            obj.delete()
        return Response({'hash':'yes'},status=status.HTTP_200_OK)
    else:
        obj, created = DayLeft.objects.get_or_create(user=OcularUser.objects.filter().last())
        print(obj)
        if created:
            obj.stop_date = timezone.now() + datetime.timedelta(7)
            obj.save()
        return Response({'hash': 'no', 'date_end':obj.stop_date.strftime('%d-%m-%Y')}, status=status.HTTP_200_OK)
