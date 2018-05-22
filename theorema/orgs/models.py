from django.db import models
from django.contrib.postgres.fields import JSONField

class Organization(models.Model):
    name = models.CharField(max_length=400)

    def __str__(self):
        return self.name

class OcularUser(models.Model):
    hardware_hash=models.CharField(max_length=50)
    max_cam=JSONField(default=list)

