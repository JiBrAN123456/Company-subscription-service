from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    CompanyViewset, SubscriptionPlanViewset,
    SubscriptionViewset, PaymentViewset
)

router = DefaultRouter()
router.register('companies', CompanyViewset)
router.register('plans', SubscriptionPlanViewset)
router.register('subscriptions', SubscriptionViewset)
router.register('payments', PaymentViewset)

urlpatterns = [
    path('', include(router.urls)),
]