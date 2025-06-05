from django.apps import AppConfig


class PayrollConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payroll'
    verbose_name = 'Staff Payroll Management'

    def ready(self):
        import payroll.signals
