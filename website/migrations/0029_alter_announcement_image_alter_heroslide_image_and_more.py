# Generated by Django 5.1.6 on 2025-06-13 06:35

import website.models
import website.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0028_sitesettings_favicon'),
    ]

    operations = [
        migrations.AlterField(
            model_name='announcement',
            name='image',
            field=models.ImageField(blank=True, null=True, storage=website.storage.get_cloudinary_storage, upload_to='announcements/'),
        ),
        migrations.AlterField(
            model_name='heroslide',
            name='image',
            field=models.ImageField(storage=website.storage.get_cloudinary_storage, upload_to='hero_slides/'),
        ),
        migrations.AlterField(
            model_name='pagecontent',
            name='calendar_placeholder_image',
            field=models.ImageField(blank=True, help_text='Placeholder image for the calendar widget', null=True, storage=website.storage.get_cloudinary_storage, upload_to='page_content/'),
        ),
        migrations.AlterField(
            model_name='pagecontent',
            name='image',
            field=models.ImageField(blank=True, help_text='Image for this section.', null=True, storage=website.storage.get_cloudinary_storage, upload_to=website.models.PageContent.get_upload_path),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='favicon',
            field=models.ImageField(blank=True, help_text='Website icon (favicon) displayed in browser tabs. Recommended size: 32x32 or 16x16 pixels. If not provided, the school logo will be used.', null=True, storage=website.storage.get_cloudinary_storage, upload_to='site/favicon/'),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='footer_logo',
            field=models.ImageField(blank=True, help_text='Optional different logo for footer', null=True, storage=website.storage.get_cloudinary_storage, upload_to='site/'),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='school_logo',
            field=models.ImageField(help_text='Main school logo displayed in the header', storage=website.storage.get_cloudinary_storage, upload_to='site/'),
        ),
    ]
