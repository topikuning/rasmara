from django.apps import AppConfig


class MasterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.master"
    label = "master"
    verbose_name = "Master Data (Company, PPK, MasterFacility, MasterWorkCode)"

    def ready(self) -> None:
        # Daftarkan model ke audit signal
        from apps.core import signals as core_signals
        from . import models as m

        core_signals.AUDITED_MODELS.update({
            m.Company, m.PPK, m.MasterFacility, m.MasterWorkCode,
        })
