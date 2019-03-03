from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import User, CamSet
from .serializers import UserSerializer, CamSetSerializer
from theorema.cameras.models import Camera, CameraGroup
from theorema.cameras.serializers import CameraSerializer, CameraGroupSerializer
from theorema.other.cache_fix import CacheFixViewSet

class UserViewSet(CacheFixViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            param = self.request.query_params.get('organization', None)
            if param is not None:
                return queryset.filter(organization__id=param)
            return queryset
        if self.request.user.is_organization_admin:
            return queryset.filter(organization=self.request.user.organization)
        return queryset.filter(id=self.request.user.id)


@api_view()
def profile_view(request):
    if request.user.is_anonymous:
        raise PermissionDenied()
    return Response(UserSerializer(request.user).data)

@api_view()
def user_cameras(request):
    if request.user.is_anonymous:
        raise PermissionDenied()
    if not request.user.cameras_access:
        user_groups = []
    else:
        user_groups = request.user.cameras_access.get('groups', [])
    groups_ids = [x['group'] for x in user_groups]
    if not groups_ids:
        if request.user.is_staff:
            groups_objects = CameraGroup.objects.all()
        else:
            groups_objects = CameraGroup.objects.filter(organization=request.user.organization)
    else:
        groups_objects = CameraGroup.objects.filter(id__in=groups_ids)
    camera_group_serializer = CameraGroupSerializer()
    camera_serializer = CameraSerializer(context={'request': request})
    result = {'groups': []}
    for group_object in groups_objects:
        group_repr = camera_group_serializer.to_representation(group_object)
        if group_object.id not in groups_ids:
            cameras_objects = Camera.objects.filter(camera_group=group_object)
        else:
           user_cameras_for_this_group = list(filter(lambda x: x['group'] == group_object.id, user_groups))[0]['cameras']
           if not user_cameras_for_this_group:
               cameras_objects = Camera.objects.filter(camera_group=group_object)
           else:
               cameras_objects = Camera.objects.filter(id__in=user_cameras_for_this_group)
        group_repr['cameras'] = []
        for camera_object in cameras_objects:
            camera_repr = camera_serializer.to_representation(camera_object, with_group=False)
            camera_repr['output_url'] = 'rtmp://{}:1935/videoanalytic/'.format(camera_object.server.address)
            camera_repr['output_vascaled_url'] = 'rtmp://{}:1935/vascaled/'.format(camera_object.server.address)
            camera_repr['output_vasrc_url'] = 'rtmp://{}:1935/vasrc/'.format(camera_object.server.address)
            camera_repr['events_url'] = 'http://{}:{}/'.format(camera_object.server.address, camera_object.port)

            camera_repr['http_output_url'] = '/videoanalytic/cam{}/index.m3u8'.format(camera_object.id)
            camera_repr['http_output_vascaled_url'] = '/vascaled/cam{}/index.m3u8'.format(camera_object.id)
            camera_repr['http_output_vasrc_url'] = '/vasrc/cam{}/index.m3u8'.format(camera_object.id)
            group_repr['cameras'].append(camera_repr)
        result['groups'].append(group_repr)
    return Response(result)


class CamSetViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = CamSet.objects.all()
    serializer_class = CamSetSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            return queryset.filter(user=self.request.user)
        return queryset
