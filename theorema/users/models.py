from django.contrib.auth.models import AbstractUser
from django.db import models
from django.dispatch import receiver


class User(AbstractUser):
    fio = models.CharField(max_length=300)
    is_chief_guard = models.BooleanField(default=False)
    tab_security = models.BooleanField(default=True)
    tab_records = models.BooleanField(default=True)
    tab_settings = models.BooleanField(default=True)
    tab_cameras = models.BooleanField(default=True)

'''
# https://stackoverflow.com/questions/26786512/how-to-see-if-a-field-changed-in-model-save-method
@receiver(models.signals.pre_save, sender=User)
def hash_pass(sender, instance, **kwargs):
    try:
        current_instance = sender.objects.get(id=instance.id)
        if current_instance.password != instance.password:
            instance.set_password(instance.password)
    except sender.DoesNotExist:
        instance.set_password(instance.password)
'''
