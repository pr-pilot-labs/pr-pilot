class TaskEngine:
    def __init__(self, task: Task, max_steps=5):
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
        self.generate_task_title()
        self.clone_github_repo()
        working_branch = None
        # If task is a PR, checkout the PR branch

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

    def clone_github_repo(self):
        TaskEvent.add(actor="assistant", action="clone_repo", target=self.task.github_project, message="Cloning repository")
        logger.info(f"Cloning repo {self.task.github_project} to {settings.REPO_DIR}")
        if os.path.exists(settings.REPO_DIR):
            logger.info(f"Deleting existing directory contents.")
            shutil.rmtree(settings.REPO_DIR)
        git_repo_url = f'https://x-access-token:{self.github_token}@github.com/{self.task.github_project}.git'
        git.Repo.clone_from(git_repo_url, settings.REPO_DIR)
        logger.info(f"Cloned repo {self.task.github_project} to {settings.REPO_DIR}")

    # Other methods remain unchanged