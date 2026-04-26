from rest_framework.routers import DefaultRouter

from .views import (
    AddendumViewSet,
    FieldObservationViewSet,
    VariationOrderViewSet,
    VOItemViewSet,
)

router = DefaultRouter()
router.register("vos", VariationOrderViewSet, basename="vo")
router.register("vo-items", VOItemViewSet, basename="vo-item")
router.register("addenda", AddendumViewSet, basename="addendum")
router.register("field-observations", FieldObservationViewSet, basename="field-observation")

urlpatterns = router.urls
