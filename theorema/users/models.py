from django.contrib.auth.models import AbstractUser
from django.db import models
from django.dispatch import receiver
from django.contrib.postgres.fields import JSONField
from theorema.orgs.models import Organization
from theorema.cameras.models import CameraGroup

class User(AbstractUser):
    fio = models.CharField(max_length=300)
    is_organization_admin = models.BooleanField(default=False)
    organization = models.ForeignKey(Organization, null=True)
    cameras_access = JSONField(null=True)

# https://stackoverflow.com/questions/26786512/how-to-see-if-a-field-changed-in-model-save-method
@receiver(models.signals.pre_save, sender=User)
def hash_pass(sender, instance, **kwargs):
    try:
        current_instance = sender.objects.get(id=instance.id)
        if current_instance.password != instance.password:
            instance.set_password(instance.password)
    except sender.DoesNotExist:
        instance.set_password(instance.password)


class CamSet(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=500)
    cameras = JSONField(null=True)
    mode = models.SmallIntegerField(default=0)

