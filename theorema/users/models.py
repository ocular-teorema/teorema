from django.contrib.auth.models import AbstractUser
from django.db import models
from django.dispatch import receiver
from theorema.orgs.models import Organization
from theorema.cameras.models import CameraGroup

class User(AbstractUser):
    fio = models.CharField(max_length=300)
    is_organization_admin = models.BooleanField(default=False)
    organization = models.ForeignKey(Organization, null=True)
    camera_group = models.ForeignKey(CameraGroup, null=True)
