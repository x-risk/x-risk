# -*- coding: utf-8 -*-
# Generated by Django 1.11.28 on 2020-03-24 12:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0006_auto_20200319_1817'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='educational_attainment',
            field=models.IntegerField(choices=[(0, 'No formal education'), (1, 'Secondary school'), (2, 'Degree'), (3, 'Masters'), (4, 'Doctorate'), (5, 'Postdoctoral Research or equivalent')], default=0),
        ),
    ]
