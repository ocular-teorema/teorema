# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2020-02-06 10:42
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cameras', '0015_camera_address_secondary'),
    ]

    operations = [
        migrations.AlterField(
            model_name='camera',
            name='onvif_port',
            field=models.IntegerField(default=80),
        ),
    ]