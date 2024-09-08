from django.urls import path
from . import views

urlpatterns = [
    path("skills/", views.skill_list, name="skill_list"),
]
