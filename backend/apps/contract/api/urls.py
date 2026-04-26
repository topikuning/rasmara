from rest_framework.routers import DefaultRouter

from .views import ContractViewSet, FacilityViewSet, LocationViewSet

router = DefaultRouter()
router.register("contracts", ContractViewSet, basename="contract")
router.register("locations", LocationViewSet, basename="location")
router.register("facilities", FacilityViewSet, basename="facility")

urlpatterns = router.urls
