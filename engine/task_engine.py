import logging
from decimal import Decimal
from django.db.models import Sum
from github.PullRequest import PullRequest
from accounts.models import UserBudget
from engine.agents.pr_pilot_agent import create_pr_pilot_agent
from engine.models import Task, TaskEvent, CostItem
from engine.project import Project
from engine.project_manager import ProjectManager
from engine.github_client import GitHubClient
from engine.task_utils import generate_task_title_wrapper

logger = logging.getLogger(__name__)

class TaskEngine:

    def __init__(self, task: Task, max_steps=5):
        self.task = task
        self.max_steps = max_steps
        self.executor = create_pr_pilot_agent()
        self.project_manager = ProjectManager(Project(name=task.github_project, main_branch=task.default_branch))
        self.github_client = GitHubClient(task.installation_id, task.github_project)
        self.project = Project(name=task.github_project, main_branch=task.default_branch)

    def run(self) -> str:
        self.task.status = "running"
        self.task.save()
        generate_task_title_wrapper(self.task)
        self.project_manager.clone_github_repo()
        # If task is a PR, checkout the PR branch
        if self.task.pr_number:
            TaskEvent.add(actor="assistant", action="checkout_pr_branch", target=self.task.head, message="Checking out PR branch")
            self.project.checkout_branch(self.task.head)
            working_branch = self.task.head
        else:
            working_branch = self.project_manager.setup_working_branch(self.task.title)
        try:
            # Make sure we never work directly on the main branch
            if self.project.active_branch == self.project.main_branch:
                raise ValueError(f"Cannot work on the main branch {self.project.main_branch}.")
            executor_result = self.executor.invoke({"user_request": self.task.user_request, "github_project": self.task.github_project})
            self.task.result = executor_result['output']
            self.task.status = "completed"
            final_response = executor_result['output']
            if working_branch and self.task.pr_number:
                # We are working on an existing PR
                if self.project.get_diff_to_main():
                    logger.info(f"Found changes on {working_branch!r} branch. Pushing ...")
                    self.project.push_branch(working_branch)
            elif working_branch and self.project_manager.finalize_working_branch(working_branch):
                # We are working on a new branch and have changes to push
                logger.info(f"Creating pull request for branch {working_branch}")
                pr: PullRequest = self.project.create_pull_request(title=self.task.title, body=final_response, head=working_branch)
                final_response += f"\n\n**PR**: [{pr.title}]({pr.html_url})\n\nIf you require further changes, continue our conversation over there!"
            final_response += f"\n\n📋[Task Log](https://app.pr-pilot.ai/dashboard/tasks/{str(self.task.id)}/)"
        except Exception as e:
            self.task.status = "failed"
            self.task.result = str(e)
            logger.error("Failed to run task", exc_info=e)
            dashboard_link = f"[Your Dashboard](https://app.pr-pilot.ai/dashboard/tasks/{str(self.task.id)}/)"
            final_response = f"I'm sorry, something went wrong, please check {dashboard_link} for details."
        finally:
            self.task.save()
            total_cost = sum([item.credits for item in CostItem.objects.filter(task=self.task)])
            if total_cost:
                logger.info(f"Total cost of task: {total_cost} credits")
                budget = UserBudget.get_user_budget(self.task.github_user)
                budget.budget = budget.budget - Decimal(str(total_cost))
                logger.info(f"Remaining budget for user {self.task.github_user}: {budget.budget} credits")
                budget.save()
            else:
                logger.warning(f"No cost items found for task {self.task.title}")
        self.task.response_comment.edit(final_response)
        return final_response
