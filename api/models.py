"""
Django app: api
"""

from django.db import models


class ApiKey(models.Model):
    title = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    encrypted_key = models.CharField(max_length=255)

    def __str__(self):
        return self.title
