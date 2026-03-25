"""
transactions/apps.py
"""

from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "transactions"
    verbose_name       = "Transactions"

    def ready(self):
        """
        Called once when Django has fully loaded all models.
        Starts the background fine-sync daemon thread.

        The guard inside fine_sync.start_auto_sync() ensures the thread
        is only created once even if ready() is called twice by Django's
        autoreloader (RUN_MAIN env-var trick is handled inside fine_sync).
        """
        # Only start the background thread in the main worker process,
        # not during management commands like migrate, collectstatic, etc.
        import os
        import sys

        # Skip in management commands — avoids DB hits before migrations run.
        _mgmt_commands = {"migrate", "makemigrations", "collectstatic", "shell",
                          "test", "check", "inspectdb", "showmigrations",
                          "squashmigrations", "flush", "dbshell"}
        if len(sys.argv) > 1 and sys.argv[1] in _mgmt_commands:
            return

        # Django dev-server forks: only run in the reloader child process
        # (RUN_MAIN=true) to avoid starting two threads at once.
        if os.environ.get("RUN_MAIN") == "true" or not _is_dev_server():
            from .fine_sync import start_auto_sync
            start_auto_sync()


def _is_dev_server() -> bool:
    """True when running via `manage.py runserver`."""
    import sys
    return len(sys.argv) > 1 and sys.argv[1] == "runserver"