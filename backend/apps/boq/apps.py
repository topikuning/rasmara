from django.apps import AppConfig


class BoqConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.boq"
    label = "boq"
    verbose_name = "BOQ (Bill of Quantity)"

    def ready(self) -> None:
        from apps.core import signals as core_signals
        from . import models as m

        core_signals.AUDITED_MODELS.update({m.BOQRevision, m.BOQItem})
        # Connect signal: auto-create V0 saat Contract dibuat
        from . import signals as boq_signals  # noqa: F401
