from rest_framework.routers import DefaultRouter

from .views import BOQItemViewSet, BOQRevisionViewSet

router = DefaultRouter()
router.register("boq-revisions", BOQRevisionViewSet, basename="boq-revision")
router.register("boq-items", BOQItemViewSet, basename="boq-item")

urlpatterns = router.urls
