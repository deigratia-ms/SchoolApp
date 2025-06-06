# Generated by Django 5.1.6 on 2025-04-15 01:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0006_event_show_on_website'),
        ('website', '0015_pagecontent_button_link_pagecontent_button_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='management_event',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='website_event', to='communications.event'),
        ),
    ]
