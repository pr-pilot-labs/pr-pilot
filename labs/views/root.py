from django.shortcuts import render
from labs.models import Experiment

def root(request):
    existing_experiments = Experiment.objects.order_by("-created_at").all()[:20]
    return render(
        request,
        "lab_root.html",
        {"experiments": existing_experiments, "title": "Arcane Engineering Labs"},
    )
