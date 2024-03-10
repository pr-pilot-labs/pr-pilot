import yaml
from jinja2 import FileSystemLoader, Environment, select_autoescape
from kubernetes import config
from kubernetes.client import BatchV1Api

from engine.util import slugify


class KubernetesJob:

    def __init__(self, task):
        self.task = task

    def spawn(self):
        # Load kubeconfig
        config.load_kube_config()

        # Load the Jinja2 template
        file_loader = FileSystemLoader('.')
        env = Environment(loader=file_loader, autoescape=select_autoescape())
        template = env.get_template('job_template.yaml.j2')
        labels = {
            "task_id": str(self.task.id),
            "github_project": self.task.github_project,
            "github_user": self.task.github_user,
            "branch": self.task.branch,

        }
        # Render the template with variables
        rendered_template = template.render(
            job_name=slugify(self.task.title),
            labels=labels,
            task_id=str(self.task.id),
        )

        # Load the rendered template as a Kubernetes object
        job_object = yaml.safe_load(rendered_template)

        # Create the job
        batch_v1 = BatchV1Api()
        return batch_v1.create_namespaced_job(body=job_object, namespace="default")