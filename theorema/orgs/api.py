
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
#        md5hash = hashlib.md5()
#        print(1)
#        byte_str=bytes(str(subprocess.check_output('lspci', shell=True)), encoding='utf=8')
#        print(2)
#        md5hash.update(byte_str)
#        print(3)
#        hash = md5hash.hexdigest()      
#        print(4)
        hash=str(random.choice(range(123123123123)))
        response = requests.post('http://78.46.97.176:1234/account', json={'hash':hash, 'new_user': 'true'})
        print(5)
        if response.json()['status'] == 'ok':
            print(response.json())
            OcularUser.objects.create(hardware_hash=hash, max_cam=response.json()['max_cams'])
            Response(response, status=status.HTTP_200_OK)
        else:
             raise APIException(code=400, detail={'status': 1, 'message': 'something wrong'})
    else:
        pass
    return Response({'message':'already_register'}, status=status.HTTP_200_OK)
