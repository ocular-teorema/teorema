# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2019-12-13 05:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cameras', '0012_auto_20191212_1717'),
    ]

    operations = [
        migrations.AlterField(
            model_name='camera',
            name='schedule_job_start',
            field=models.CharField(default=None, max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='camera',
            name='schedule_job_stop',
            field=models.CharField(default=None, max_length=150, null=True),
        ),
    ]