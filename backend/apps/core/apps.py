from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
    verbose_name = "Core (Auth, RBAC, Audit)"

    def ready(self) -> None:
        # Import signals supaya audit log terpasang
        from . import signals  # noqa: F401
