"""Settings production VPS."""
from .base import *  # noqa: F401,F403
from .env import env_bool

DEBUG = False

# Security headers — sebagian aktif hanya saat ada TLS.
# Saat akses awal HTTP via IP, biarkan defaultnya (akan jadi aktif begitu pakai HTTPS).
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", default=False)
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=False)
SECURE_HSTS_SECONDS = 0  # nyalakan setelah TLS aktif via env override
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
