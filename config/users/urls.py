from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from users.views import (
    UserViewSet,
    PaymentViewSet,
    UserRegistrationAPIView,
    PaymentSuccessView,
    PaymentCancelView,
    PaymentStatusView,
    SubscriptionAPIView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', UserRegistrationAPIView.as_view(), name='user-register'),
    path('subscriptions/', SubscriptionAPIView.as_view(), name='subscription'),
    path('payments/success/', PaymentSuccessView.as_view(), name='payment-success'),
    path('payments/cancel/', PaymentCancelView.as_view(), name='payment-cancel'),
    path('payments/<int:payment_id>/status/', PaymentStatusView.as_view(), name='payment-status'),]