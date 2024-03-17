import logging
from engine.project import Project
from engine.util import slugify
from git import Repo
from django.conf import settings

logger = logging.getLogger(__name__)

class TaskEngineBranchManagement:
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
        """Create a new branch based on the given branch name basis.
        :param branch_name_basis: String to use for generating the branch name
        :return: Branch name
        """

        # This method will use the Project class's methods to manage branches
        pass

    def finalize_working_branch(self, branch_name: str) -> bool:
        """Finalize the working branch by committing and pushing changes.
        :param branch_name: Name of the working branch
        :return: True if changes were pushed, False if no changes were made
        """
        # This method will use the Project class's methods to manage branches
        pass
