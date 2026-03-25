from django.apps import AppConfig


class SuperuserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name         = 'superuser'
    label        = 'superuser'
    verbose_name = 'SaaS Superuser Dashboard'

    def ready(self):
        pass  # register signals here if needed
