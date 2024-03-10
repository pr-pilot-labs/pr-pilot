from django.contrib.auth.models import AbstractUser
from django.db import models


class PilotUser(AbstractUser):
    pass

class UserBudget(models.Model):
    username = models.CharField(max_length=200)
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=5)

    def __str__(self):
        return f"Budget {self.username} - ${self.budget}"

    @staticmethod
    def get_user_budget(username):
        budget = UserBudget.objects.get(username=username)
        if not budget:
            return UserBudget.objects.create(username=username)
        return budget

