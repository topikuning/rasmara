"""Settings dev lokal."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

# Email -> Mailpit
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Storage -> filesystem lokal saat dev (lebih cepat). Switch ke 's3' kalau mau
# uji MinIO via STORAGE_BACKEND=s3 di .env
