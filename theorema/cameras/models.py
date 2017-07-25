from django.db import models
from django.core.validators import RegexValidator
from theorema.orgs.models import Organization

class Server(models.Model):
    name = models.CharField(max_length=100)
    address = models.GenericIPAddressField()
    organization = models.ForeignKey(Organization)


class CameraGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
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
    fps = models.SmallIntegerField(default=10)
    analysis = models.SmallIntegerField(choices=CameraAnalysisTypes, default=1)
    resolution = models.SmallIntegerField(choices=CameraResolutions, default=1)
    storage_life = models.IntegerField(default=7)
    compress_level = models.SmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    camera_group = models.ForeignKey(CameraGroup)
    server = models.ForeignKey(Server)
    organization = models.ForeignKey(Organization)


class Camera2CameraGroup(models.Model):
    camera = models.ForeignKey(CameraGroup)
    camera_group = models.ForeignKey(Camera)


