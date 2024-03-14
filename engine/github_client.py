from github import Github, GithubException
from github.PullRequest import PullRequest
from engine.util import slugify
from webhooks.jwt_tools import get_installation_access_token

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self, installation_id, github_project):
        self.github_token = get_installation_access_token(installation_id)
        self.github = Github(self.github_token)
        self.github_repo = self.github.get_repo(github_project)

    def create_unique_branch_name(self, basis: str):
        """Create branch name based on a given string. If branch exists,
        add increasing numbers at the end"""
        unique_branch_name = f"pr-pilot/{slugify(basis)}"[:50]
        repo = self.github.get_repo(self.github_repo.full_name)

        counter = 1
        original_branch_name = unique_branch_name
        while unique_branch_name in [branch.name for branch in repo.get_branches()]:
            unique_branch_name = f"{original_branch_name}-{counter}"
            counter += 1
        return unique_branch_name
