from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from django_tables2 import SingleTableView

from dashboard.tables import TaskTable, EventTable
from engine.models import Task


# Create your views here.
class TaskListView(SingleTableView, LoginRequiredMixin):
    model = Task
    table_class = TaskTable
    template_name = 'task_list.html'

    def get_queryset(self):
        # Filter the tasks by the logged-in user's ID
        return Task.objects.filter(github_user=self.request.user.username)

class TaskDetailView(DetailView, LoginRequiredMixin):
    model = Task
    template_name = 'task_detail.html'
    context_object_name = 'task'

    def get_queryset(self):
        # Filter the queryset to only include tasks owned by the logged-in user
        return Task.objects.filter(github_user=self.request.user.username)

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

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Get the task from the context
        task = context['task']
        # Create an EventTable instance with the task's events
        context['event_table'] = EventTable(task.events.all())
        return context