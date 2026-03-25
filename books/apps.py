from django.apps import AppConfig


class BooksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "books"
    verbose_name       = "Library Books"

    def ready(self):
        # Import signals here when needed, e.g.:
        # import books.signals  # noqa: F401
        pass