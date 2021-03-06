"""theorema URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from rest_framework.routers import DefaultRouter

from .users.api import UserViewSet, profile_view, user_cameras, CamSetViewSet
from .cameras.api import ServerViewSet, CameraViewSet, CameraGroupViewSet,NotificationViewSet, add_cams, QuadratorViewSet
from .orgs.api import OrganizationViewSet, OcularUserViewSet, update_ocularuser_info , update_ocularuser_info_offline,cam_pay
from .other.views import index, login, stat, video


router = DefaultRouter(trailing_slash=True)
router.register(r'users', UserViewSet)
router.register(r'servers', ServerViewSet)
router.register(r'cameras', CameraViewSet)
router.register(r'camera_groups', CameraGroupViewSet)
router.register(r'organizations', OrganizationViewSet)
router.register(r'camsets', CamSetViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'ocularuser', OcularUserViewSet)
router.register(r'quadrator', QuadratorViewSet)

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include(router.urls)),
    url(r'^accounts/profile/', profile_view),
    url(r'^api/rest-auth/', include('rest_auth.urls')),
    url(r'stat/', stat),
    url(r'user_cameras/', user_cameras),
    url(r'api/update_ocularuser_info', update_ocularuser_info),
    url(r'api/update_ocularuser_info_offline', update_ocularuser_info_offline),
    url(r'api/cam_pay', cam_pay),
    url(r'api/offline_pay', add_cams),
#    url(r'api/today_hash', get_today_hash),
]


urlpatterns += url(r'^login', login),
urlpatterns += url(r'^video.html', video),
urlpatterns += url(r'^/*', index, name='all'),
