import logging
import os
from engine.task_engine import TaskEngine
from engine.models.task import Task

logger = logging.getLogger(__name__)

class TaskWorker:
    def __init__(self, queue):
        self.queue = queue

    def start(self):
        while True:
            message = self.queue.get()
            if message == 'STOP':
                break
            task = Task.objects.get(id=message['task_id'])
            task_engine = TaskEngine(task)
            task_engine.run()
            logger.info(f"Task {task.id} processed")