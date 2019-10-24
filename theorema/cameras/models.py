import datetime
from django.db import models
from django.core.validators import RegexValidator
from django.contrib.postgres.fields import JSONField
from theorema.orgs.models import Organization

SERVER_TYPES = [
    ('full', 'full'),
    ('analysis', 'analysis'),
    ('storage', 'storage')
]
class Server(models.Model):
    parent_server_id=models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=100)
    address = models.GenericIPAddressField()
    local_address = models.GenericIPAddressField(default='0.0.0.0')
    organization = models.ForeignKey(Organization)
    type = models.CharField(choices=SERVER_TYPES, default='full', max_length=8)


class CameraGroup(models.Model):
    name = models.CharField(max_length=100)
    organization = models.ForeignKey(Organization)




CameraAnalysisTypes = [
    (1, 'Full'),
    (2, 'Move'),
    (3, 'Record'),
]

CameraResolutions = [
    (1, '360'),
    (2, '480'),
    (3, '720'),
    (4, 'HD'),
    (5, '2K'),
    (6, '4K'),
]

class Camera(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=400)
    fps = models.SmallIntegerField(default=10) # deprecated
    analysis = models.SmallIntegerField(choices=CameraAnalysisTypes, default=1)
    resolution = models.SmallIntegerField(choices=CameraResolutions, default=1) # deprecated
    storage_life = models.IntegerField(default=7)
    compress_level = models.SmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    camera_group = models.ForeignKey(CameraGroup)
    server = models.ForeignKey(Server)
    organization = models.ForeignKey(Organization)
    port = models.IntegerField()
    notify_email = models.CharField(max_length=500, null=True)
    notify_phone = models.CharField(max_length=20, null=True)
    notify_events = JSONField(default={})
    notify_time_start = models.TimeField(default=datetime.time(0,0))
    notify_time_stop = models.TimeField(default=datetime.time(0,0))
    notify_alert_level = models.SmallIntegerField(default=1)
    notify_send_email = models.BooleanField(default=False)
    notify_send_sms = models.BooleanField(default=False)
    indefinitely = models.BooleanField(default=False)
    archive_path=models.CharField(max_length=512, blank=True, null=True)
    add_time = models.CharField(max_length=50, blank=True, null=True)


class Camera2CameraGroup(models.Model):
    camera = models.ForeignKey(CameraGroup)
    camera_group = models.ForeignKey(Camera)


class NotificationCamera(models.Model):
    organization = models.ForeignKey(Organization, blank=True, null=True)
    users = models.ManyToManyField('users.User')
    camera = JSONField(null=True)
    camera_group =JSONField(null=True)
    notify_events = JSONField(default={})
    notify_time_start = models.TimeField(default=datetime.time(0,0))
    notify_time_stop = models.TimeField(default=datetime.time(0,0))
    notify_alert_level = models.SmallIntegerField(default=1)


class Quadrator(models.Model):
    name = models.CharField(max_length=100)
    num_cam_x = models.IntegerField()
    num_cam_y = models.IntegerField()
    output_width = models.IntegerField()
    output_height = models.IntegerField()
    output_FPS = models.IntegerField()
    output_quality = models.IntegerField()
    port = models.IntegerField()
    organization = models.ForeignKey(Organization)
    server = models.ForeignKey(Server)

class Camera2Quadrator(models.Model):
    camera = models.ForeignKey(Camera)
    quadrator = models.ForeignKey(Quadrator)
    x = models.IntegerField(default=0)
    y = models.IntegerField(default=0)
    cols = models.IntegerField(default=1)
    rows = models.IntegerField(default=1)
