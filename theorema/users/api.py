from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserSerializer
from theorema.cameras.models import Camera, CameraGroup
from theorema.cameras.serializers import CameraSerializer, CameraGroupSerializer

class UserViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            param = self.request.query_params.get('organization', None)
            if param is not None:
                return self.queryset.filter(organization__id=param)
            return self.queryset
        if self.request.user.is_organization_admin:
            return self.queryset.filter(organization=self.request.user.organization)
        return self.queryset.filter(id=self.request.user.id)


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
        groups_objects = CameraGroup.objects.filter(organization=request.user.organization)
    else:
        groups_objects = CameraGroup.objects.filter(id__in=groups_ids)
    camera_group_serializer = CameraGroupSerializer()
    camera_serializer = CameraSerializer()
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
            camera_repr['output_url'] = 'rtmp://{}:1935/vascaled/cam{}'.format(camera_object.server.address, camera_object.id)
            camera_repr['events_url'] = 'http://{}:{}/'.format(camera_object.server.address, camera_object.port)
            group_repr['cameras'].append(camera_repr)
        result['groups'].append(group_repr)
    return Response(result)
