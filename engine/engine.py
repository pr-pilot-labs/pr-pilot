from django.conf import settings
from git import Repo

from engine.models import TaskEvent
from engine.project import Project, logger
from engine.util import slugify


class Engine:
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
        project = Project.from_github()
        project.discard_all_changes()
        project.fetch_remote()
        project.checkout_latest_default_branch()
        tool_branch = self.create_unique_branch_name(branch_name_basis)
        logger.info(f"Creating new local branch '{tool_branch}'...")
        TaskEvent.add(actor="assistant", action="create_branch", target=tool_branch)
        project.create_new_branch(tool_branch)
        return tool_branch


    def finalize_working_branch(self, branch_name: str) -> bool:
        """
        Finalize the working branch by committing and pushing changes.
        :param branch_name: Name of the working branch
        :return: True if changes were pushed, False if no changes were made
        """
        project = Project.from_github()
        if project.has_uncommitted_changes():
            logger.warn(f"Found uncommitted changes on {branch_name!r} branch! Committing...")
            project.commit_all_changes(message=f"Uncommitted changes")
        if project.get_diff_to_main():
            logger.info(f"Found changes on {branch_name!r} branch. Pushing and creating PR...")
            project.push_branch(branch_name)
            TaskEvent.add(actor="assistant", action="push_branch", target=branch_name)
            project.checkout_latest_default_branch()
            return True
        else:
            logger.info(f"No changes on {branch_name} branch. Deleting...")
            project.checkout_latest_default_branch()
            project.delete_branch(branch_name)
            TaskEvent.add(actor="assistant", action="delete_branch", target=branch_name, message="No changes were made")
            return False
