from django.urls import path
from labs.views.root import root
from labs.views.create_experiment import create_experiment
from labs.views.view_experiment import view_experiment
from labs.views.copy_experiment import copy_experiment

urlpatterns = [
    path("", root, name="experiment_home"),
    path(
        "<str:github_user>/<str:github_repo>/new/",
        create_experiment,
        name="experiment_create",
    ),
    path(
        "<str:github_user>/<str:github_repo>/<str:slug>/",
        view_experiment,
        name="experiment_view",
    ),
    path(
        "<str:github_user>/<str:github_repo>/<str:slug>/copy/",
        copy_experiment,
        name="experiment_copy",
    ),
]
