# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2020-01-22 12:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cameras', '0008_auto_20191025_1215'),
    ]

    operations = [
        migrations.AddField(
            model_name='quadrator',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='quadrator',
            name='last_ping_time',
            field=models.IntegerField(default=1579695904.575161),
        ),
    ]