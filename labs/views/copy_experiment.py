import time
from django.shortcuts import render
from github import Github, GithubException
from labs.views.create_experiment import collect_skills_for_new_experiment
from labs.models import Experiment
from prpilot import settings

def copy_experiment(request, github_user, github_repo, slug):
    """Same as create_experiment but with pre-filled instructions and knowledge."""
    try {
        g = Github(settings.LABS_GITHUB_TOKEN)
        repo = g.get_repo(f"{github_user}/{github_repo}")
    except GithubException as e:
        return render(request, "error.html", {"error": e})

    try {
        experiment = Experiment.objects.filter(slug=slug).last()
    except Experiment.DoesNotExist:
        return render(request, "error.html", {"error": "Experiment not found."})

    if request.method == "GET":
        organized_skills = collect_skills_for_new_experiment(repo)
        return render(
            request,
            "create_experiment.html",
            {
                "repo": repo,
                "title": f"New Experiment for {repo.full_name}",
                "instructions": experiment.task.user_request,
                "knowledge": experiment.knowledge,
                "skills": organized_skills,
            },
        )
    else:
        return render(request, "error.html", {"error": "Method not allowed."})
