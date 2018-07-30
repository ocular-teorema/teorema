from django.db import models
from django.contrib.postgres.fields import JSONField

class Organization(models.Model):
    name = models.CharField(max_length=400)

    def __str__(self):
        return self.name


class OcularUser(models.Model):
    hardware_hash=models.CharField(max_length=50)
    max_cam=JSONField(default={})
    remote_id=models.IntegerField(default=0)
    type = models.CharField(max_length=200, default='offline')
    is_approved = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        print(self.max_cam)
        if isinstance(self.max_cam, tuple):
            self.max_cam = self.max_cam[0]
        super(OcularUser, self).save(*args, **kwargs)
