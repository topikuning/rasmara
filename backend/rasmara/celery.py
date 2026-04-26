"""Celery app RASMARA."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rasmara.settings.dev")

app = Celery("rasmara")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self) -> None:
    print(f"Request: {self.request!r}")
