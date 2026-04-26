from rest_framework.routers import DefaultRouter

from .views import (
    CompanyViewSet,
    MasterFacilityViewSet,
    MasterWorkCodeViewSet,
    PPKViewSet,
)

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("ppks", PPKViewSet, basename="ppk")
router.register("master-facilities", MasterFacilityViewSet, basename="master-facility")
router.register("master-work-codes", MasterWorkCodeViewSet, basename="master-work-code")

urlpatterns = router.urls
