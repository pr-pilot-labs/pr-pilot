from django.urls import path
from . import views

urlpatterns = [
    path("skills/", views.skill_list, name="skill_list"),
    path("search/", views.skill_search, name="skill_search"),
]
