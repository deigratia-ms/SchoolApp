from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0018_alter_studentquizchoice_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignment',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('PUBLISHED', 'Published'),
                    ('ARCHIVED', 'Archived')
                ],
                default='PUBLISHED',
                max_length=20
            ),
        ),
    ]
