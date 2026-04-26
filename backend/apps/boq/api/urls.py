from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BOQCompareView, BOQItemViewSet, BOQRevisionViewSet

router = DefaultRouter()
router.register("boq-revisions", BOQRevisionViewSet, basename="boq-revision")
router.register("boq-items", BOQItemViewSet, basename="boq-item")

# Comparison: nested by contract — manual binding karena DRF router kurang
# fleksibel utk URL kwargs nested.
compare_list = BOQCompareView.as_view({"get": "list"})
compare_xlsx = BOQCompareView.as_view({"get": "export_xlsx"})

urlpatterns = router.urls + [
    path("contracts/<uuid:contract_id>/boq-compare/", compare_list,
          name="boq-compare-list"),
    path("contracts/<uuid:contract_id>/boq-compare/export-xlsx/", compare_xlsx,
          name="boq-compare-xlsx"),
]
