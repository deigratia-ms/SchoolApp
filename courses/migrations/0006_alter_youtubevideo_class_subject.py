# Generated by Django 5.1.6 on 2025-04-03 20:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0005_allow_null_teachers'),
    ]

    operations = [
        migrations.AlterField(
            model_name='youtubevideo',
            name='class_subject',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='videos', to='courses.classsubject'),
        ),
    ]
