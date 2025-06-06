# Generated by Django 5.1.6 on 2025-03-21 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0008_assignment_questions_to_display'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignment',
            name='randomize_choices',
            field=models.BooleanField(default=True, help_text='Whether to randomize the order of multiple choice answers. Can be disabled for younger students.'),
        ),
        migrations.AddField(
            model_name='assignment',
            name='randomize_questions',
            field=models.BooleanField(default=True, help_text='Whether to randomize the order of questions. Can be disabled for younger students.'),
        ),
    ]
