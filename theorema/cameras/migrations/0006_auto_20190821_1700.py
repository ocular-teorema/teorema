# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2019-08-21 14:00
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cameras', '0005_auto_20190815_1957'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='quadratorgroup',
            name='organization',
        ),
        migrations.RemoveField(
            model_name='quadrator',
            name='quadrator_group',
        ),
        migrations.DeleteModel(
            name='QuadratorGroup',
        ),
    ]