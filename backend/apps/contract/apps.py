from django.apps import AppConfig


class ContractConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contract"
    label = "contract"
    verbose_name = "Kontrak (Contract, Location, Facility)"

    def ready(self) -> None:
        from apps.core import signals as core_signals
        from . import models as m

        core_signals.AUDITED_MODELS.update({
            m.Contract, m.Location, m.Facility,
        })
