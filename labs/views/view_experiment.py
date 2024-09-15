import markdown
from django.shortcuts import render
from github import Github, GithubException
from labs.views.create_experiment import render_markdown, icon_for_action
from labs.models import Experiment
from prpilot import settings

def view_experiment(request, github_user, github_repo, slug):
    try {
        g = Github(settings.LABS_GITHUB_TOKEN)
        repo = g.get_repo(f"{github_user}/{github_repo}")
    except GithubException as e:
        return render(request, "error.html", {"error": e})

    try {
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

    experiment.task.user_request = render_markdown(experiment.task.user_request)
    if experiment.task.result:
        experiment.task.result = render_markdown(experiment.task.result)

    skills = list(experiment.skills.all())
    for skill in skills:
        skill.instructions = render_markdown(skill.instructions)

    return render(
        request,
        "view_experiment.html",
        {
            "repo": repo,
            "experiment": experiment,
            "skills": skills,
            "task_events": task_events,
            "icon_for_action": icon_for_action,
            "title": f"AE Labs - {experiment.name}",
        },
    )
