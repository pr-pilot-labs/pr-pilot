from django.urls import path
from . import views

urlpatterns = [
    # Other URL patterns...
    path('profile/', views.user_profile, name='user_profile'),
    path('github/webhook/', views.github_webhook, name='github_webhook'),
    path('permissions/', views.repository_permissions, name='github_permissions'),
]
