# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2019-08-15 16:57
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='quadrator_access',
            field=django.contrib.postgres.fields.jsonb.JSONField(null=True),
        ),
    ]
