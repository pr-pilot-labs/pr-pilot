from django.db import models


# Create your models here.
class Experiment(models.Model):
    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    task = models.ForeignKey("engine.Task", on_delete=models.CASCADE)
    skills = models.ManyToManyField("hub.PilotSkill")
    knowledge = models.TextField()
    github_project = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name
