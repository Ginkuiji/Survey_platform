from rest_framework_simplejwt.views import TokenObtainPairView
from .serializer import EmailTokenObtainPairSerializer

class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer