from django.shortcuts import render
from django.utils.safestring import mark_safe
import markdown
from .models import PilotSkill


def render_markdown(markdown_text):
    return mark_safe(
        markdown.markdown(markdown_text.replace("<", "&lt;").replace(">", "&gt;"))
    )


def skill_list(request):
    skills = PilotSkill.objects.all()
    projects = set([skill.github_repo.full_name for skill in skills])

    for skill in skills:
        skill.instructions = render_markdown(skill.instructions)
        skill.result = render_markdown(skill.result)

    return render(
        request, "hub/skill_list.html", {"skills": skills, "projects": projects}
    )


def skill_search(request):
    query = request.GET.get("q", "")
    results = []
    if query:
        results = PilotSkill.objects.filter(
            title__icontains=query
        ) | PilotSkill.objects.filter(instructions__icontains=query)
        for skill in results:
            skill.instructions = render_markdown(skill.instructions)
            skill.result = render_markdown(skill.result)
    return render(request, "hub/search.html", {"query": query, "results": results})
