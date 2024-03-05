from django.contrib.auth.models import AbstractUser
from django.db import models


class PilotUser(AbstractUser):
    # Add additional fields here
    pass


class GitHubAccount(models.Model):
    account_id = models.IntegerField(unique=True)
    login = models.CharField(max_length=255)
    avatar_url = models.URLField(max_length=2000)
    html_url = models.URLField(max_length=2000)

    def __str__(self):
        return self.login

class GitHubAppInstallation(models.Model):
    installation_id = models.IntegerField(unique=True)
    account = models.OneToOneField(GitHubAccount, on_delete=models.CASCADE, related_name='installation')
    installed_at = models.DateTimeField(auto_now_add=True)
    access_tokens_url = models.URLField(max_length=2000)
    repositories_url = models.URLField(max_length=2000)
    app_id = models.IntegerField()
    target_id = models.IntegerField()
    target_type = models.CharField(max_length=255)

    def __str__(self):
        return f"Installation {self.installation_id} for account {self.account.login}"



class GitHubRepository(models.Model):
    installation = models.ForeignKey(GitHubAppInstallation, on_delete=models.CASCADE, related_name='repositories')
    repository_id = models.IntegerField(unique=True)
    node_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    private = models.BooleanField(default=True)

    def __str__(self):
        return self.full_name