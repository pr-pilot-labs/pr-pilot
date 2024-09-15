from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Experiment
from hub.meta import generate_metadata
from django_q.tasks import async_task

@receiver(post_save, sender=Experiment)
def create_metadata_task(sender, instance, created, **kwargs):
    if created:
        async_task('labs.signals.generate_and_save_metadata', instance.id)


def generate_and_save_metadata(experiment_id):
    from .models import Experiment
    experiment = Experiment.objects.get(id=experiment_id)
    metadata = generate_metadata(experiment.description)
    experiment.metadata = metadata.json()
    experiment.save()