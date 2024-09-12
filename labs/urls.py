from django.urls import path
from . import views

urlpatterns = [
    path("", views.root, name="experiment_home"),
    path(
        "<str:github_user>/<str:github_repo>/new/",
        views.create_experiment,
        name="experiment_create",
    ),
    path(
        "<str:github_user>/<str:github_repo>/<str:slug>/",
        views.view_experiment,
        name="experiment_view",
    ),
    path(
        "<str:github_user>/<str:github_repo>/<str:slug>/copy/",
        views.copy_experiment,
        name="experiment_copy",
    ),
]
