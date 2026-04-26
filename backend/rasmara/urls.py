"""Root URL conf RASMARA."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from common.views import HealthView, ReadyView, VersionView

api_v1_patterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("health/ready/", ReadyView.as_view(), name="ready"),
    path("version/", VersionView.as_view(), name="version"),
    path("auth/", include("apps.core.urls.auth")),
    path("", include("apps.core.urls.rbac")),
    path("", include("apps.master.api.urls")),
    path("", include("apps.contract.api.urls")),
    path("", include("apps.boq.api.urls")),
    path("", include("apps.change.api.urls")),
]

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/", include((api_v1_patterns, "api_v1"))),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
