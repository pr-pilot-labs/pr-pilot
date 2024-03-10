import logging
import os
import shutil

import git
from django.conf import settings
from git import Repo
from github import Github, GithubException
from langchain_openai import ChatOpenAI

from engine.agents.pr_pilot_agent import create_pr_pilot_agent
from engine.langchain.generate_pr_info import generate_pr_info, LabelsAndTitle
from engine.langchain.generate_task_title import generate_task_title
from engine.models import Task, TaskEvent
from engine.project import Project
from engine.util import slugify
from webhooks.jwt_tools import get_installation_access_token

logger = logging.getLogger(__name__)

# Initialize model
gpt_4_turbo = ChatOpenAI(model="gpt-4-turbo-preview", openai_api_key=settings.OPENAI_API_KEY, temperature=0)
gpt_4 = ChatOpenAI(model="gpt-4", openai_api_key=settings.OPENAI_API_KEY, temperature=0)
gpt_3_5_turbo = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=settings.OPENAI_API_KEY, temperature=0)

class TaskEngine:

    def __init__(self, task: Task, max_steps=5):
        self.task = task
        self.max_steps = max_steps
        self.executor = create_pr_pilot_agent()
        self.github_token = get_installation_access_token(self.task.installation_id)
        self.github = Github(self.github_token)
        self.github_repo = self.github.get_repo(self.task.github_project)
        self.project = Project(name=self.github_repo.full_name, main_branch=self.github_repo.default_branch)


    def create_unique_branch_name(self, basis: str):
        """Create branch name based on a given string. If branch exists,
        add increasing numbers at the end"""
        unique_branch_name = f"pr-pilot/{slugify(basis)}"[:50]
        repo = Repo(settings.REPO_DIR)

        counter = 1
        original_branch_name = unique_branch_name
        while unique_branch_name in repo.branches:
            unique_branch_name = f"{original_branch_name}-{counter}"
            counter += 1
        return unique_branch_name

    def setup_working_branch(self, branch_name_basis: str):
        """
        Create a new branch based on the given branch name basis.
        :param branch_name_basis: String to use for generating the branch name
        :return: Branch name
        """

        self.project.discard_all_changes()
        self.project.fetch_remote()
        self.project.checkout_latest_default_branch()
        tool_branch = self.create_unique_branch_name(branch_name_basis)
        logger.info(f"Creating new local branch '{tool_branch}'...")
        TaskEvent.add(actor="assistant", action="create_branch", target=tool_branch)
        self.project.create_new_branch(tool_branch)
        return tool_branch


    def finalize_working_branch(self, branch_name: str) -> bool:
        """
        Finalize the working branch by committing and pushing changes.
        :param branch_name: Name of the working branch
        :return: True if changes were pushed, False if no changes were made
        """
        if self.project.has_uncommitted_changes():
            logger.warn(f"Found uncommitted changes on {branch_name!r} branch! Committing...")
            self.project.commit_all_changes(message=f"Uncommitted changes")
        if self.project.get_diff_to_main():
            logger.info(f"Found changes on {branch_name!r} branch. Pushing and creating PR...")
            self.project.push_branch(branch_name)
            TaskEvent.add(actor="assistant", action="push_branch", target=branch_name)
            self.project.checkout_latest_default_branch()
            return True
        else:
            logger.info(f"No changes on {branch_name} branch. Deleting...")
            self.project.checkout_latest_default_branch()
            self.project.delete_branch(branch_name)
            TaskEvent.add(actor="assistant", action="delete_branch", target=branch_name, message="No changes were made")
            return False

    def generate_task_title(self):
        if self.task.pr_number:
            pr = self.github_repo.get_pull(self.task.pr_number)
            self.task.title = generate_task_title(pr.body, self.task.user_request)
        else:
            issue = self.github_repo.get_issue(self.task.issue_number)
            self.task.title = generate_task_title(issue.body, self.task.user_request)
        self.task.save()


    def run(self) -> str:
        self.task.status = "running"
        self.task.save()
        self.clone_github_repo()
        self.generate_task_title()
        working_branch = None
        # If task is a PR, checkout the PR branch
        if self.task.pr_number:
            self.project.checkout_branch(self.task.head)
        else:
            working_branch = self.setup_working_branch(self.task.title)
        try:
            # Make sure we never work directly on the main branch
            if self.project.active_branch == self.project.main_branch:
                raise ValueError(f"Cannot work on the main branch {self.project.main_branch}.")
            executor_result = self.executor.invoke({"user_request": self.task.user_request})
            self.task.result = executor_result['output']
            self.task.status = "completed"
            final_response = executor_result['output']
            if working_branch and self.finalize_working_branch(working_branch):
                # We have changes, create a PR
                logger.info(f"Creating pull request for branch {working_branch}")
                pr_info = generate_pr_info(final_response)
                if not pr_info:
                    pr_info = LabelsAndTitle(title=self.task.title, labels=["darwin"])
                pr = Project.from_github().create_pull_request(title=pr_info.title, body=final_response,
                                                               head=working_branch, labels=pr_info.labels)
                final_response += f"\n\nPull request has been created: [#{pr.number}]({pr.html_url})"
        except Exception as e:
            self.task.status = "failed"
            self.task.result = str(e)
            logger.error("Failed to run task", exc_info=e)
            final_response = f"I'm sorry, something went wrong, please check [Your Dashboard](https:/app.pr-pilot.ai) for details."
        finally:
            self.task.save()
        if self.task.pr_number:
            # Respond to the user's comment on the PR
            self.project.push_branch(self.task.head)
            logger.info(f"Responding to user's comment on PR {self.task.pr_number}")
            pr = self.github_repo.get_pull(self.task.pr_number)
            try:
                pr.create_review_comment_reply(self.task.comment_id, final_response)
            except GithubException as e:
                if e.status == 404:
                    pr.create_issue_comment(final_response)
                else:
                    raise
        elif self.task.issue_number:
            # Respond to the user's comment on the issue
            logger.info(f"Responding to user's comment on issue {self.task.issue_number}")
            issue = self.github_repo.get_issue(self.task.issue_number)
            issue.create_comment(final_response)
        TaskEvent.add(actor="assistant", action="run_task", target=self.task.title, message=final_response, transaction="end")
        return final_response

    def clone_github_repo(self):
        logger.info(f"Cloning repo {self.task.github_project} to {settings.REPO_DIR}")
        if os.path.exists(settings.REPO_DIR):
            logger.info(f"Deleting existing directory contents.")
            shutil.rmtree(settings.REPO_DIR)
        git_repo_url = f'https://x-access-token:{self.github_token}@github.com/{self.task.github_project}.git'
        git.Repo.clone_from(git_repo_url, settings.REPO_DIR)
        logger.info(f"Cloned repo {self.task.github_project} to {settings.REPO_DIR}")

