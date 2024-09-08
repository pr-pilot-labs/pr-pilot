from django.db import models


class PilotSkill(models.Model):
    title = models.CharField(null=False, blank=False, max_length=255)
    instructions = models.TextField(null=False, blank=False)
    result = models.TextField(null=False, blank=False)
    github_repo = models.ForeignKey(
        "webhooks.GithubRepository", on_delete=models.CASCADE, related_name="skills"
    )


class PilotSkillArgument(models.Model):
    key = models.CharField(null=False, blank=False, max_length=255)
    value = models.CharField(null=False, blank=False, max_length=255)
    skill = models.ForeignKey(
        PilotSkill, on_delete=models.CASCADE, related_name="arguments"
    )
