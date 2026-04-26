from django.apps import AppConfig


class ChangeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.change"
    label = "change"
    verbose_name = "Change Management (VO & Addendum)"

    def ready(self) -> None:
        from apps.core import signals as core_signals
        from . import models as m

        core_signals.AUDITED_MODELS.update({m.Addendum})
