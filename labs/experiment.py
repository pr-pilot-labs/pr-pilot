# flake8: noqa: E402

import logging
import os
import time
from typing import List

import django


django.setup()


from engine.agents.skills import AgentSkill
from engine.task_engine import TaskEngine
from webhooks.models import GithubRepository
from django.conf import settings
from github import Github
from engine.models.task import Task


logger = logging.getLogger(__name__)


def run_experiment(
    repo: str, instructions: str, knowledge: str, skills: List[AgentSkill] = ()
):
    """Fork the repo, create TaskEngine instance, and run the experiment."""
    g = Github(settings.LABS_GITHUB_TOKEN)
    user = g.get_user()
    repo = g.get_repo(repo)
    fork = user.create_fork(repo)
    print(f"Forked repository: {fork.full_name}")
    # Wait for the fork installation to be created
    while not GithubRepository.objects.filter(full_name=fork.full_name).exists():
        print("Waiting for installation to be created...")
        time.sleep(2)
    installed_repo = GithubRepository.objects.get(full_name=fork.full_name)
    task = Task.objects.create(
        user_request=instructions,
        github_user="pr-pilot-labs",
        github_project=fork.full_name,
        installation_id=installed_repo.installation.installation_id,
    )
    settings.TASK_ID = str(task.id)
    os.environ["TASK_ID"] = str(task.id)
    engine = TaskEngine(task)
    engine.run(
        additional_knowledge=knowledge,
        overwrite_pilot_skills=[
            skill.to_agent_tool(task, repo.description, knowledge) for skill in skills
        ],
    )
    print(task.result)
    # task.schedule()


if __name__ == "__main__":
    knowledge = ""
    instructions = """
    Reflect on the content of a directory:
    1. List the directory
    2. If there is a README.md in it, read it
    3. From the information you gathered, deduce whatever you can about the directory:
    - Are there any modules defined?
    - Does it hint to specific libraries or frameworks being used?
    - Are there any tests?
    - Are there any configuration files?
    - What is the purpose of the directory?
    4. Summarize your findings in a concise list of bullet points.
    
    Examples of bullet points:
    - Directory defines Django app 'myapp'
    - Babel used for transpiling in `babel.config.js`
    - `src` directory contains the main source code
    - `test` directory contains unit tests
    - `package.json` defines the project dependencies
    """
    skills = [
        AgentSkill(
            title="Reflect on a directory",
            instructions=instructions,
            args={
                "dir_path": "Path to the directory to reflect on",
                "info_about_parent": "(Optional) Information about the parent directory",
            },
            result="A concise list of bullet points",
        )
    ]
    run_experiment(
        "pr-pilot-ai/pr-pilot",
        "Reflect on the '.' directory. Then, reflect on each of its direct subdirectories. Respond with a concise, technical description of the project.",
        knowledge,
        skills,
    )
