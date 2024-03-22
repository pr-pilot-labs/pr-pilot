from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView

from accounts.models import UserSettings


@login_required
def user_logout(request):
    # Log out the user
    logout(request)
    # Redirect to home page (or any other page you prefer)
    return redirect('/')


def home(request):
    if request.user.is_authenticated:
        # Redirect to dashboard
        return redirect('task_list')
    else:
        return redirect('/accounts/github/login/?method=oauth2')


def health_check(request):
    return HttpResponse("OK")


class TaskUndoView(LoginRequiredMixin, DetailView):
    model = UserSettings
    template_name = 'user_settings.html'
    context_object_name = 'settings'

    def get_queryset(self):
        # Filter the queryset to only include tasks owned by the logged-in user
        return UserSettings.objects.filter(username=self.request.user.username)

    def get_object(self, queryset=None):
        """Override get_object to ensure task ownership."""
        if queryset is None:
            queryset = self.get_queryset()
        # Make sure to catch the task based on the passed ID and check ownership
        pk = self.kwargs.get(self.pk_url_kwarg)
        task = get_object_or_404(queryset, pk=pk)

        # Check if the task belongs to the logged-in user
        if task.github_user != self.request.user.username:
            raise Http404("You do not have permission to view this task.")

        return task