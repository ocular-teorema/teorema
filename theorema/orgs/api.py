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
from theorema.settings import lk_url

class OrganizationViewSet(ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

class OcularUserViewSet(ModelViewSet):
    queryset = OcularUser.objects.all()
    serializer_class = OcularUserSerializer
    
    def get_queryset(self):
        return OcularUser.objects.all()


# online version
#Этот метод следует вызывать при создании объекта ocularUser, а так же для обновления информации о камерах
@api_view(['GET'])
def update_ocularuser_info(request):
    print(lk_url)
    if not OcularUser.objects.exists():
        md5hash = hashlib.md5()
        byte_str=bytes(str(subprocess.check_output('lspci', shell=True)), encoding='utf=8')
        md5hash.update(byte_str)
        hash = md5hash.hexdigest()
        user = OcularUser.objects.create(hardware_hash=hash)
    else:
        user = OcularUser.objects.filter().last()
        hash = user.hardware_hash
    try:
        response = requests.post('{}api/v1/get_user_info'.format(lk_url), {'hash':hash})
    except:
        return Response({"status" : "bad request"})
    v = response.json()
    print(response)
    if response.json()['exist'] == True:
        user.max_cam=response.json()['max_cams'],
        user.remote_id=response.json()['user_id']
        user.save()
        return Response({"status": "userinfo_update"}, status=status.HTTP_200_OK)
    else:
        return Response({"status": "user_not_exist"})



#offline_version
#Этот метод используется для оффлайн регистрации и оффлайнового добавления камер
#Вызывать его следует только тогда, когда предыдущий запрос вернул "bad_request"
@api_view(['POST'], )
def update_ocularuser_info_offline(request):
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
        print(user_cameras)
        user.max_cam = user_cameras
        return Response({"status":"update"})
    else:
        return Response({"status": "wrong_code"})


@api_view(['POST'], )
def cam_pay(request):
    '''
    {"user_id":19,
    "cam":{
        "f":12,
        "s":4,
        "a":2
    },
    "sum":256
    }

    '''
    cam = request.data['cam']
    user_id = OcularUser.objects.filter().last().remote_id
    sum = request.data['sum']
    try:
        result = requests.post('{}api/v1/cam_pay/'.format(lk_url),
                               json={'user_id': user_id, 'cam': cam, "sum": sum})
        print(result)
        if result.json()['success_url'] != None:
            return Response(result.json())
    except:
        return Response({'succes_url':'something wrong'})


'''
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
'''