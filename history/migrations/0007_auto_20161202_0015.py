# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-12-02 00:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0006_domain_opened_from_tabid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='page',
            name='title',
            field=models.CharField(max_length=1000),
        ),
    ]
