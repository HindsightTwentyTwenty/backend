# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-09 00:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0005_domain_opened_from_domain'),
    ]

    operations = [
        migrations.AddField(
            model_name='domain',
            name='opened_from_tabid',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
