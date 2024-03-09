import markdown
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_tables2 import tables, A

from engine.models import Task, TaskEvent


class GithubProjectLinkColumn(tables.columns.Column):

    def render(self, value):
        return format_html('<a href="https://github.com/{}" target="_blank">{}</a>', value, value)


class TaskStatusColumn(tables.columns.Column):

        def render(self, value):
            color = 'success'
            if value == 'scheduled':
                color = 'primary'
            elif value == 'running':
                color = 'warning'
            elif value == 'failed':
                color = 'danger'
            return format_html('<span class="badge bg-{}">{}</span>', color, value)


class MarkdownColumn(tables.columns.Column):
    def render(self, value):
        # Convert Markdown to HTML and mark it safe for rendering
        return mark_safe(markdown.markdown(value))


class TaskTable(tables.Table):
    title = tables.columns.RelatedLinkColumn("task_detail", args=[A("pk")])
    github_project = GithubProjectLinkColumn()
    status = TaskStatusColumn()

    def render_title(self, value):
        # Truncate the title to 50 characters
        return value[:50] + '...' if len(value) > 50 else value

    class Meta:
        model = Task
        order_by = ('-created',)
        template_name = "django_tables2/bootstrap5.html"
        fields = ("created", "title", "status", "github_project")

class EventTable(tables.Table):
    message = MarkdownColumn()

    class Meta:
        model = TaskEvent  # Use the model associated with the events
        fields = ['timestamp', 'action', 'target', 'message']