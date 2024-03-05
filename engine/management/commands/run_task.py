from django.core.management.base import BaseCommand, CommandError

from engine.models import Task
from engine.task_engine import TaskEngine


class Command(BaseCommand):
    help = 'Run a task.'

    def add_arguments(self, parser):
        parser.add_argument('task_id', type=str)

    def handle(self, *args, **options):
        task_id = options['task_id']
        task = Task.objects.get(id=task_id)
        engine = TaskEngine(task)
        engine.run()
