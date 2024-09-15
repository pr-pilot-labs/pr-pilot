import time
from django.shortcuts import render, redirect
from github import Github, GithubException
from engine.models.task import Task
from engine.task_scheduler import SchedulerError
from engine.util import slugify
from hub.models import PilotSkill
from labs.generate_title import generate_experiment_title
from labs.models import Experiment
from prpilot import settings
from webhooks.models import GithubRepository

def create_experiment(request, github_user, github_repo):
    try {
        g = Github(settings.LABS_GITHUB_TOKEN)
        repo = g.get_repo(f"{github_user}/{github_repo}")
    except GithubException as e:
        return render(request, "error.html", {"error": e})

    if request.method == "POST":
        instructions = request.POST.get("instructions")
        knowledge = request.POST.get("knowledge")
        skill_ids = [x for x in request.POST.get("selected_skill_ids").split(",") if x]
        user = g.get_user()
        fork = user.create_fork(repo)
        fork.edit(has_wiki=True, has_issues=True)
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
        title = generate_experiment_title(
            github_project=repo.full_name,
            github_project_description=repo.description,
            knowledge=knowledge,
            instructions=instructions,
        )

        slug = slugify(title)
        while Experiment.objects.filter(slug=slug).exists():
            slug = slugify(title + "-" + str(time.time()))

        experiment = Experiment.objects.create(
            name=title,
            slug=slug,
            knowledge=knowledge,
            task=task,
            github_project=repo.full_name,
        )
        if skill_ids:
            experiment.skills.set(PilotSkill.objects.filter(id__in=skill_ids).all())
            experiment.save()
        try {
            task.schedule()
        except SchedulerError as e:
            return render(request, "error.html", {"error": e})

        return redirect(
            "experiment_view",
            github_user=github_user,
            github_repo=github_repo,
            slug=experiment.slug,
        )
    elif request.method == "GET":
        organized_skills = collect_skills_for_new_experiment(repo)
        return render(
            request,
            "create_experiment.html",
            {
                "repo": repo,
                "title": f"New Experiment for {repo.full_name}",
                "skills": organized_skills,
            },
        )

def collect_skills_for_new_experiment(repo):
    core_skills = PilotSkill.objects.filter(
        github_repo__full_name="PR-Pilot-AI/core"
    ).all()
    repo_skills = PilotSkill.objects.filter(github_repo__full_name=repo.full_name).all()
    skills = set(core_skills).union(repo_skills)
    for skill in skills:
        skill.instructions = render_markdown(skill.instructions)
    # Eliminate duplicates by name
    skills = {skill.title: skill for skill in skills}.values()
    organized_skills = {}
    for skill in skills:
        if skill.category not in organized_skills:
            organized_skills[skill.category] = []
        organized_skills[skill.category].append(skill)
    return organized_skills

def render_markdown(markdown_text):
    return mark_safe(markdown.markdown(markdown_text))

def icon_for_action(action):
    ACTION_FA_ICON_MAP = {
        "invoke_skill": "forward",
        "finish_skill": "backward",
        "push_branch": "code-branch",
        "checkout_branch": "code-branch",
        "write_file": "edit",
        "list_directory": "folder",
        "search_code": "search",
        "search": "search",
        "search_issues": "search",
        "read_github_issue": "file-alt",
        "read_pull_request": "file-alt",
        "read_files": "file-alt",
    }
    return ACTION_FA_ICON_MAP.get(action, "circle-check")
