import time

import markdown
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe
from github import Github, GithubException

from engine.models.task import Task
from engine.util import slugify
from labs.generate_title import generate_experiment_title
from labs.models import Experiment
from prpilot import settings
from webhooks.models import GithubRepository


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


def icon_for_action(action):
    return ACTION_FA_ICON_MAP.get(action, "circle-check")


def render_markdown(markdown_text):
    return mark_safe(markdown.markdown(markdown_text))


def root(request):
    existing_experiments = Experiment.objects.all()
    # Sorted by date created
    existing_experiments = sorted(
        existing_experiments, key=lambda x: x.created_at, reverse=True
    )
    return render(
        request,
        "lab_root.html",
        {"experiments": existing_experiments, "title": "Arcane Engineering Labs"},
    )


def copy_experiment(request, github_user, github_repo, slug):
    """Same as create_experiment but with pre-filled instructions and knowledge."""
    try:
        g = Github(settings.LABS_GITHUB_TOKEN)
        repo = g.get_repo(f"{github_user}/{github_repo}")
    except GithubException as e:
        return render(request, "error.html", {"error": e})

    try:
        experiment = Experiment.objects.filter(slug=slug).last()
    except Experiment.DoesNotExist:
        return render(request, "error.html", {"error": "Experiment not found."})

    if request.method == "GET":
        # Get knowledge and instructions from the existing experiment
        return render(
            request,
            "create_experiment.html",
            {
                "repo": repo,
                "title": f"New Experiment for {repo.full_name}",
                "instructions": experiment.task.user_request,
                "knowledge": experiment.knowledge,
            },
        )
    else:
        return render(request, "error.html", {"error": "Method not allowed."})


def view_experiment(request, github_user, github_repo, slug):
    try:
        g = Github(settings.LABS_GITHUB_TOKEN)
        repo = g.get_repo(f"{github_user}/{github_repo}")
    except GithubException as e:
        return render(request, "error.html", {"error": e})

    try:
        experiment = Experiment.objects.filter(slug=slug).last()
        experiment.knowledge = render_markdown(experiment.knowledge)
    except Experiment.DoesNotExist:
        return render(request, "error.html", {"error": "Experiment not found."})

    task_events = sorted(experiment.task.events.all(), key=lambda x: x.timestamp)
    indent = 0
    for event in task_events:

        event.indent = indent
        event.icon = icon_for_action(event.action)
        event.message = render_markdown(event.message)
        event.seconds_since_start = round(
            (event.timestamp - task_events[0].timestamp).total_seconds()
        )
        if event.action == "invoke_skill":
            indent += 1
        elif event.action == "finish_skill":
            indent -= 1

    if experiment.task.result:
        experiment.task.result = render_markdown(experiment.task.result)

    return render(
        request,
        "view_experiment.html",
        {
            "repo": repo,
            "experiment": experiment,
            "task_events": task_events,
            "icon_for_action": icon_for_action,
            "title": f"AE Labs - {experiment.name}",
        },
    )


def create_experiment(request, github_user, github_repo):
    try:
        g = Github(settings.LABS_GITHUB_TOKEN)
        repo = g.get_repo(f"{github_user}/{github_repo}")
    except GithubException as e:
        return render(request, "error.html", {"error": e})

    if request.method == "POST":
        instructions = request.POST.get("instructions")
        knowledge = request.POST.get("knowledge")
        user = g.get_user()
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
            name=title, slug=slug, knowledge=knowledge, task=task
        )
        task.schedule()

        return redirect(
            "experiment_view",
            github_user=github_user,
            github_repo=github_repo,
            slug=experiment.slug,
        )
    elif request.method == "GET":

        return render(
            request,
            "create_experiment.html",
            {"repo": repo, "title": f"New Experiment for {repo.full_name}"},
        )
