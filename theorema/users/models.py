from django.contrib.auth.models import AbstractUser
from django.db import models
from django.dispatch import receiver
from django.contrib.postgres.fields import JSONField
from theorema.orgs.models import Organization
from theorema.cameras.models import CameraGroup
import pytz

class User(AbstractUser):
    fio = models.CharField(max_length=300, blank=True)
    is_organization_admin = models.BooleanField(default=False)
    organization = models.ForeignKey(Organization, null=True)
    cameras_access = JSONField(null=True)
    phone=models.CharField(max_length=30, blank=True)
    timezone = models.CharField(max_length=256, blank=True)

# https://stackoverflow.com/questions/26786512/how-to-see-if-a-field-changed-in-model-save-method
@receiver(models.signals.pre_save, sender=User)
def hash_pass(sender, instance, **kwargs):
    if not instance.is_superuser:
        instance.set_password(instance.password)
'''
    try:
        current_instance = sender.objects.get(id=instance.id)
        if current_instance.password != instance.password:
            instance.set_password(instance.password)
    except sender.DoesNotExist:
        instance.set_password(instance.password)
'''


class CamSet(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=500)
    cameras = JSONField(null=True)
    mode = models.SmallIntegerField(default=0)

