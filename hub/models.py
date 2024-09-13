import logging

from django.db import models

from hub.meta import generate_metadata


logger = logging.getLogger(__name__)


class ProgrammingLanguage(models.Model):
    name = models.CharField(
        null=False, blank=False, max_length=255, unique=True, primary_key=True
    )


class ProgrammingFramework(models.Model):
    name = models.CharField(
        null=False, blank=False, max_length=255, unique=True, primary_key=True
    )


class Tag(models.Model):
    name = models.CharField(
        null=False, blank=False, max_length=255, unique=True, primary_key=True
    )


class PilotSkill(models.Model):
    title = models.CharField(null=False, blank=False, max_length=255)
    instructions = models.TextField(null=False, blank=False)
    result = models.TextField(null=False, blank=False)
    github_repo = models.ForeignKey(
        "webhooks.GithubRepository", on_delete=models.CASCADE, related_name="skills"
    )
    category = models.CharField(null=True, blank=True, default="Other", max_length=255)
    programming_languages = models.ManyToManyField(
        ProgrammingLanguage, related_name="skills"
    )
    programming_frameworks = models.ManyToManyField(
        ProgrammingFramework, related_name="skills"
    )
    tags = models.ManyToManyField(Tag, related_name="skills")
    fa_icon_classes = models.CharField(null=True, blank=True, max_length=255)

    def __str__(self):
        return f"{self.github_repo.full_name} - {self.title}"

    def generate_meta_data(self):
        logger.info(f"Generating metadata for skill {self.title}")
        content = (
            f"This is an AI agent skill.\n\n"
            f"Title: {self.title}\n\n"
            f"Arguments: {', '.join([f'{arg.key}={arg.value}' for arg in self.arguments.all()])}\n\n"
            f"Instructions: {self.instructions}\n\n"
            f"Expected Result: {self.result}"
        )
        meta = generate_metadata(content)
        self.category = meta.category
        self.fa_icon_classes = meta.fa_icon_classes
        self.tags.set([Tag.objects.get_or_create(name=tag)[0] for tag in meta.tags])
        self.programming_languages.set(
            [
                ProgrammingLanguage.objects.get_or_create(name=lang)[0]
                for lang in meta.languages
            ]
        )
        self.programming_frameworks.set(
            [
                ProgrammingFramework.objects.get_or_create(name=framework)[0]
                for framework in meta.frameworks
            ]
        )
        self.save()


class PilotSkillArgument(models.Model):
    key = models.CharField(null=False, blank=False, max_length=255)
    value = models.CharField(null=False, blank=False, max_length=255)
    skill = models.ForeignKey(
        PilotSkill, on_delete=models.CASCADE, related_name="arguments"
    )
