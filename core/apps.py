from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # This imports the signals.py file when the Django server starts
        # Without this, the @receiver functions will never trigger.
        import core.signals