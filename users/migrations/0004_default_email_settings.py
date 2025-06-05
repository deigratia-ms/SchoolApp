from django.db import migrations

def create_default_settings(apps, schema_editor):
    SchoolSettings = apps.get_model('users', 'SchoolSettings')
    if not SchoolSettings.objects.exists():
        SchoolSettings.objects.create(
            smtp_host='smtp.gmail.com',
            smtp_port=587,
            smtp_username='skillnetservices@gmail.com',
            smtp_password='aikc fcil iauc tmmt',
            smtp_use_tls=True
        )

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0003_schoolsettings_academic_year_and_more'),
    ]

    operations = [
        migrations.RunPython(create_default_settings),
    ]