# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2020-01-16 13:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cameras', '0013_auto_20191213_0850'),
    ]

    operations = [
        migrations.AddField(
            model_name='camera',
            name='onvif_password',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='camera',
            name='onvif_port',
            field=models.IntegerField(default=80),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='camera',
            name='onvif_username',
            field=models.CharField(max_length=50, null=True),
        ),
    ]