# Generated by Django 3.1.4 on 2020-12-21 10:29

import django.contrib.postgres.fields.hstore
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0047_auto_20200810_1415'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='location_data',
            field=django.contrib.postgres.fields.hstore.HStoreField(null=True),
        ),
    ]
