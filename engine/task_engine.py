import logging
import os
import shutil
from decimal import Decimal

import git
from django.conf import settings
from django.db.models import Sum
from git import Repo
from github import Github, GithubException
from langchain_openai import ChatOpenAI

from accounts.models import UserBudget
from engine.agents.pr_pilot_agent import create_pr_pilot_agent
from engine.langchain.generate_pr_info import generate_pr_info, LabelsAndTitle
from engine.langchain.generate_task_title import generate_task_title
from engine.models import Task, TaskEvent, CostItem
from engine.project import Project
from engine.util import slugify
from webhooks.jwt_tools import get_installation_access_token

logger = logging.getLogger(__name__)

class TaskEngine:

    def __init__(self, task: Task, max_steps=5):
        self.task = task
        self.max_steps = max_steps
        self.executor = create_pr_pilot_agent()
        self.github_token = get_installation_access_token(self.task.installation_id)
        self.github = Github(self.github_token)
        self.github_repo = self.github.get_repo(self.task.github_project)
        self.project = Project(name=self.github_repo.full_name, main_branch=self.github_repo.default_branch)

    # Other methods remain unchanged

    def run(self) -> str:
        self.task.status = "running"
        self.task.save()
        self.generate_task_title()
        self.clone_github_repo()
        working_branch = None

        # Post initial comment indicating the task is being worked on
        initial_comment_text = f"⏳ I'm working on it. You can follow the progress [here](https://app.pr-pilot.ai/dashboard/tasks/{str(self.task.id)}/)."
        if self.task.pr_number:
            pr = self.github_repo.get_pull(self.task.pr_number)
            initial_comment = pr.create_issue_comment(initial_comment_text)
        else:
            issue = self.github_repo.get_issue(self.task.issue_number)
            initial_comment = issue.create_comment(initial_comment_text)
        self.task.initial_comment_id = initial_comment.id
        self.task.save()

        # The rest of the method remains unchanged until the final response handling

        # Update the initial comment with the final response instead of creating a new one
        if self.task.pr_number:
            pr = self.github_repo.get_pull(self.task.pr_number)
            pr.get_issue_comment(self.task.initial_comment_id).edit(final_response)
        else:
            issue = self.github_repo.get_issue(self.task.issue_number)
            issue.get_comment(self.task.initial_comment_id).edit(final_response)

        return final_response

    # Other methods remain unchanged
