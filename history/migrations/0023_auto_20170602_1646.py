# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-06-02 16:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0022_page_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='keywords',
            field=models.TextField(default='{}'),
        ),
        migrations.AddField(
            model_name='category',
            name='num_pages',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='page',
            name='keywords',
            field=models.TextField(default='{}'),
        ),
    ]