
from rest_framework.viewsets import ModelViewSet
from .models import Organization, OcularUser
from .serializers import OrganizationSerializer, OcularUserSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
import subprocess
import hashlib
import requests
from rest_framework import status

class OrganizationViewSet(ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

class OcularUserViewSet(ModelViewSet):
    queryset = OcularUser.objects.all()
    serializer_class = OcularUserSerializer

@api_view(['GET'])
def update_ocularuser_info(request): 
    if not OcularUser.objects.exists():
        md5hash = hashlib.md5()
        print(1)
        byte_str=bytes(str(subprocess.check_output('lspci', shell=True)), encoding='utf=8')
        print(2)
        md5hash.update(byte_str)
        print(3)
        hash = md5hash.hexdigest()      
        print(4)
        response = requests.post('http://78.46.97.176:1234/account', json={'hash':hash, 'new_user': 'true'})
        print(5)
    else:
        pass
    return Response(response, status=status.HTTP_200_OK)
