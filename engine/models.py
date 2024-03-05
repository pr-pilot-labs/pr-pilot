import logging
import threading
import uuid
from functools import lru_cache

from django.conf import settings
from django.core.management import call_command
from django.db import models
from github import Github

from engine.util import run_task_in_background
from webhooks.jwt_tools import get_installation_access_token

logger = logging.getLogger(__name__)


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=200)
    created = models.DateTimeField(auto_now_add=True)
    installation_id = models.IntegerField()
    github_project = models.CharField(max_length=200)
    github_user = models.CharField(max_length=200)
    branch = models.CharField(max_length=200)
    issue_number = models.IntegerField(blank=True, null=True)
    user_request = models.TextField(blank=True)
    result = models.TextField(blank=True)

    def __str__(self):
        return self.title

    @staticmethod
    @lru_cache()
    def current():
        if not settings.TASK_ID:
            raise ValueError("TASK_ID is not set")
        return Task.objects.get(id=settings.TASK_ID)

    @property
    def github(self):
        return Github(get_installation_access_token(self.installation_id))

    @staticmethod
    def schedule(title, user_request, installation_id, github_project, github_user, branch, issue_number=None):
        new_task = Task(title=title, status="scheduled", installation_id=installation_id, github_project=github_project,
                        github_user=github_user, branch=branch, user_request=user_request, issue_number=issue_number)
        new_task.save()
        if settings.DEBUG:
            settings.TASK_ID = new_task.id
            logger.info(f"Running task in debug mode: {new_task.id}")
            thread = threading.Thread(target=run_task_in_background, args=(new_task.id,))
            thread.start()
        else:
            raise ValueError("Running tasks in production is not supported")
        return new_task


class TaskEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=200)
    action = models.CharField(max_length=200)
    target = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField(blank=True, null=True)

    @staticmethod
    def add(actor: str, action: str, target: str = None, message="", transaction=None, changes=[]):
        if not settings.TASK_ID:
            raise ValueError("TASK_ID is not set")
        new_entry = TaskEvent(actor=actor, action=action, target=target, message=message, task_id=settings.TASK_ID)
        new_entry.save()
        return new_entry


class CostItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=200)
    model_name = models.CharField(max_length=200)
    prompt_token_count = models.IntegerField()
    completion_token_count = models.IntegerField()
    requests = models.IntegerField()
    total_cost_usd = models.FloatField()

    def __str__(self):
        return f"{self.title} - ${self.total_cost_usd}"
