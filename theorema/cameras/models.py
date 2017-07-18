from django.db import models
from django.core.validators import RegexValidator

class Server(models.Model):
    name = models.CharField(max_length=100)
    address = models.GenericIPAddressField()


class CameraGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)

    
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

alnum = RegexValidator(r'^[0-9a-zA-Z]*$', 'Only English letters and digits are allowed')

class Camera(models.Model):
    cam = models.CharField(max_length=100, validators=[alnum], unique=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=400)
    fps = models.SmallIntegerField(default=10)
    analysis = models.SmallIntegerField(choices=CameraAnalysisTypes, default=1)
    resolution = models.SmallIntegerField(choices=CameraResolutions, default=1)
    storage_life = models.IntegerField(default=7)
    compress_level = models.SmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    port = models.IntegerField()
    group = models.ForeignKey(CameraGroup)


