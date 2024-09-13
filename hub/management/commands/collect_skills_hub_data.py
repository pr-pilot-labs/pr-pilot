import yaml
from django.conf import settings
from django.core.management.base import BaseCommand
from github import Github, GithubException

from engine.agents.skills import AgentSkill
from hub.models import PilotSkill
from webhooks.jwt_tools import generate_jwt, get_installation_access_token
from webhooks.models import GithubRepository


class Command(BaseCommand):
    help = "Collects .pilot-hints.md, .pilot-commands.yaml, and pilot-skills.yaml from distinct github_project values in Task model"

    def get_repos_with_skills(self):
        """Search Github for repositories containing the .pilot-skills.yaml file"""
        jwt_token = generate_jwt(int(settings.GITHUB_APP_ID), settings.PRIVATE_KEY_PATH)
        github = Github(jwt=jwt_token)
        query = "filename:.pilot-skills.yaml"
        result = github.search_code(query)
        return [item.repository.full_name for item in result]

    def scrape_pilot_skills(self, repo: GithubRepository, skills_file_content: str):
        skills = yaml.safe_load(skills_file_content)
        # Parse using Pydantic model
        agent_skills = [AgentSkill(**skill) for skill in skills]

        # Delete all existing skills for this repo
        PilotSkill.objects.filter(github_repo=repo).delete()

        # Store as Django model
        for agent_skill in agent_skills:
            pilot_skill = PilotSkill.objects.create(
                title=agent_skill.title,
                instructions=agent_skill.instructions,
                result=agent_skill.result,
                github_repo=repo,
            )
            if agent_skill.args:
                for key, value in agent_skill.args.items():
                    pilot_skill.arguments.create(key=key, value=value)
            pilot_skill.generate_meta_data()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully stored skill {agent_skill.title!r} for {repo.full_name}"
                )
            )

    def handle(self, *args, **kwargs):
        github_projects = self.get_repos_with_skills()
        for project in github_projects:
            try:
                try:
                    stored_repo = GithubRepository.objects.get(full_name=project)
                except GithubRepository.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Repository {project} not found in database, skipping."
                        )
                    )
                    continue
                g = Github(
                    get_installation_access_token(
                        stored_repo.installation.installation_id
                    )
                )
                repo = g.get_repo(project)
                if repo.private:
                    self.stderr.write(
                        self.style.WARNING(f"Skipping private repository {project}")
                    )
                    continue
                for file_name in [
                    ".pilot-hints.md",
                    ".pilot-commands.yaml",
                    ".pilot-skills.yaml",
                ]:
                    try:
                        file_content = repo.get_contents(file_name)
                        if file_name == ".pilot-skills.yaml":
                            # Check if file sha has changed
                            if file_content.sha == stored_repo.skills_file_hash:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"File {file_name} has not changed for {project}, skipping"
                                    )
                                )
                            else:
                                self.scrape_pilot_skills(
                                    stored_repo, file_content.decoded_content.decode()
                                )
                                stored_repo.skills_file_hash = file_content.sha
                                stored_repo.save()
                        elif file_name == ".pilot-hints.md":
                            stored_repo.knowledge = (
                                file_content.decoded_content.decode()
                            )
                            stored_repo.save()
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Successfully stored knowledge for {project}"
                                )
                            )
                    except GithubException as e:
                        if e.status == 404:
                            # File not found, continue
                            self.stdout.write(
                                self.style.WARNING(
                                    f"File {file_name} not found in {project}"
                                )
                            )
                            continue
                        self.stderr.write(
                            self.style.WARNING(
                                f"Could not fetch {file_name} from {project}: {e}"
                            )
                        )
            except GithubException as e:
                self.stderr.write(
                    self.style.ERROR(f"Could not access repository {project}: {e}")
                )
