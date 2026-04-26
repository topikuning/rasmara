"""Health & version endpoints."""
from django.conf import settings
from django.db import connection
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """GET /api/v1/health/  -> 200 OK."""

    permission_classes = (permissions.AllowAny,)

    def get(self, request) -> Response:
        return Response({"status": "ok"})


class ReadyView(APIView):
    """GET /api/v1/health/ready/  -> cek koneksi DB (wajib) & Redis (opsional).

    Redis hanya diperlukan saat profile=queue aktif (Celery). Stack default
    (Modul 1-4) tidak butuh Redis, jadi kegagalan ping Redis tidak menggagalkan
    health check.
    """

    permission_classes = (permissions.AllowAny,)

    def get(self, request) -> Response:
        results: dict[str, str] = {}
        ok = True

        # DB - WAJIB
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            results["database"] = "ok"
        except Exception as e:  # noqa: BLE001
            ok = False
            results["database"] = f"fail: {e}"

        # Redis - OPSIONAL (hanya cek kalau QUEUE_ENABLED=true di env)
        from rasmara.settings.env import env_bool
        if env_bool("QUEUE_ENABLED", default=False):
            try:
                import redis

                r = redis.Redis.from_url(settings.CELERY_BROKER_URL,
                                          socket_connect_timeout=2,
                                          socket_timeout=2)
                r.ping()
                results["redis"] = "ok"
            except Exception as e:  # noqa: BLE001
                ok = False
                results["redis"] = f"fail: {e}"
        else:
            results["redis"] = "disabled"

        return Response(
            {"status": "ok" if ok else "degraded", "checks": results},
            status=200 if ok else 503,
        )


class VersionView(APIView):
    """GET /api/v1/version/  -> versi build."""

    permission_classes = (permissions.AllowAny,)

    def get(self, request) -> Response:
        return Response(
            {
                "name": "RASMARA",
                "version": "0.1.0",
                "module": "fondasi",
            }
        )
