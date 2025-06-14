# Generated manually to recreate SchoolSettings table

from django.db import migrations, models
import website.storage


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_alter_admissionlettertemplate_signature_image_and_more'),
    ]

    operations = [
        # This migration is a no-op since we manually created the table
        # We're just marking the current state as applied
        migrations.RunSQL(
            "SELECT 1;",  # No-op SQL
            reverse_sql="SELECT 1;"
        ),
    ]
