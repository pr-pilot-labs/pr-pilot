import logging
import os
import shutil
from git import Repo
from django.conf import settings

logger = logging.getLogger(__name__)

class ProjectManager:
    def __init__(self, project):
        self.project = project

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
        self.project.discard_all_changes()
        self.project.fetch_remote()
        self.project.checkout_latest_default_branch()
        tool_branch = self.create_unique_branch_name(branch_name_basis)
        logger.info(f"Creating new local branch '{tool_branch}'...")
        self.project.create_new_branch(tool_branch)
        return tool_branch

    def finalize_working_branch(self, branch_name: str) -> bool:
        if self.project.has_uncommitted_changes():
            logger.warn(f"Found uncommitted changes on {branch_name!r} branch! Committing...")
            self.project.commit_all_changes(message=f"Uncommitted changes")
        if self.project.get_diff_to_main():
            logger.info(f"Found changes on {branch_name!r} branch. Pushing and creating PR...")
            self.project.push_branch(branch_name)
            self.project.checkout_latest_default_branch()
            return True
        else:
            logger.info(f"No changes on {branch_name} branch. Deleting...")
            self.project.checkout_latest_default_branch()
            self.project.delete_branch(branch_name)
            return False

    def clone_github_repo(self):
        logger.info(f"Cloning repo {self.project.github_project} to {settings.REPO_DIR}")
        if os.path.exists(settings.REPO_DIR):
            logger.info(f"Deleting existing directory contents.")
            shutil.rmtree(settings.REPO_DIR)
        git_repo_url = f'https://x-access-token:{self.project.github_token}@github.com/{self.project.github_project}.git'
        Repo.clone_from(git_repo_url, settings.REPO_DIR)
        logger.info(f"Cloned repo {self.project.github_project} to {settings.REPO_DIR}")
