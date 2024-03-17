import os
from django.conf import settings
from engine.agents.pr_pilot_agent import create_pr_pilot_agent
from engine.project import Project
from webhooks.jwt_tools import get_installation_access_token
from github import Github


class TaskEngineInit:
    def __init__(self, task, max_steps=5):
        os.environ["GIT_COMMIT_HOOK"] = ""
        self.task = task
        self.max_steps = max_steps
        self.executor = create_pr_pilot_agent()
        self.github_token = get_installation_access_token(self.task.installation_id)
        self.github = Github(self.github_token)
        self.github_repo = self.github.get_repo(self.task.github_project)
        self.project = Project(name=self.github_repo.full_name, main_branch=self.github_repo.default_branch)
