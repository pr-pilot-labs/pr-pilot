import logging
import os
import shutil

import git
from django.conf import settings
from github import Github
from langchain_openai import ChatOpenAI

from engine.agents.pr_pilot_agent import create_pr_pilot_agent
from engine.engine import Engine
from engine.langchain.generate_pr_info import generate_pr_info, LabelsAndTitle
from engine.models import Task, TaskEvent
from engine.project import Project
from webhooks.jwt_tools import get_installation_access_token

logger = logging.getLogger(__name__)

# Initialize model
gpt_4_turbo = ChatOpenAI(model="gpt-4-turbo-preview", openai_api_key=settings.OPENAI_API_KEY, temperature=0)
gpt_4 = ChatOpenAI(model="gpt-4", openai_api_key=settings.OPENAI_API_KEY, temperature=0)
gpt_3_5_turbo = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=settings.OPENAI_API_KEY, temperature=0)

class TaskEngine(Engine):

    def __init__(self, task: Task, max_steps=5, create_branch=True):
        self.task = task
        self.max_steps = max_steps
        self.create_branch = create_branch
        self.executor = create_pr_pilot_agent()

    def run(self) -> str:
        logger.info(f"Cloning repo {self.task.github_project} to {settings.REPO_DIR}")
        if os.path.exists(settings.REPO_DIR):
            logger.info(f"Deleting existing directory contents.")
            shutil.rmtree(settings.REPO_DIR)
        github_token = get_installation_access_token(self.task.installation_id)
        git_repo_url = f'https://x-access-token:{github_token}@github.com/{self.task.github_project}.git'
        git.Repo.clone_from(git_repo_url, settings.REPO_DIR)
        logger.info(f"Cloned repo {self.task.github_project} to {settings.REPO_DIR}")

        if self.create_branch:
            working_branch = self.setup_working_branch(self.task.title)
        g = Github(github_token)
        repo = g.get_repo(self.task.github_project)
        try:
            executor_result = self.executor.invoke({"user_request": self.task.user_request})
            self.task.result = executor_result['output']
            self.task.status = "completed"
            final_response = executor_result['output']
        except Exception as e:
            self.task.status = "failed"
            self.task.result = str(e)
            logger.error("Failed to run task", exc_info=e)
            final_response = f"Task run failed: {str(e)}"
        finally:
            self.task.save()
            if self.create_branch:
                found_code_changes = self.finalize_working_branch(working_branch)
                if found_code_changes:

                    pr_info = generate_pr_info(executor_result)
                    if not pr_info:
                        pr_info = LabelsAndTitle(title=self.task.title, labels=["darwin"])
                    pr = Project.from_github().create_pull_request(title=pr_info.title, body=executor_result, head=working_branch, labels=pr_info.labels)
                    final_response += f"\n\nPull request has been created: [#{pr.number}]({pr.html_url})"
        if self.task.pr_number:
            pr = repo.get_pull(self.task.pr_number)
            pr.create_review_comment_reply(self.task.comment_id, final_response)
        elif self.task.issue_number:
            issue = repo.get_issue(self.task.issue_number)
            issue.create_comment(final_response)
        TaskEvent.add(actor="assistant", action="run_task", target=self.task.title, message=final_response, transaction="end")
        return final_response

