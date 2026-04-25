# surveys/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet

router = DefaultRouter()
urlpatterns = router.urls

auth_register = AuthViewSet.as_view({
    "post": "register"
})

urlpatterns += [
    path("auth/register/", auth_register, name="auth-register"),
]