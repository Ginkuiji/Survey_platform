from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    RESPONDENT = "respondent"
    ORGANIZER = "organizer"
    ADMIN = "admin"

    ROLE_CHOICES =[
        (RESPONDENT, "Респондент"),
        (ORGANIZER, "Организатор"),
        (ADMIN, "Администратор"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=RESPONDENT,
    )

    def __str__(self):
        return self.username
# Create your models here.
