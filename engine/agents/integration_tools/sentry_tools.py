import logging
from datetime import datetime

from langchain.tools import Tool
from langchain_core.tools import StructuredTool
from pydantic.v1 import BaseModel, Field
import requests

from engine.models.task_event import TaskEvent

logger = logging.getLogger(__name__)


class SentryAPIError(Exception):
    pass


def fetch_sentry_issues(api_key: str, project_slug: str) -> str:
    url = f"https://sentry.io/api/0/projects/{project_slug}/issues/"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise SentryAPIError(f"Error fetching Sentry issues: {response.status_code}")
    issues = response.json()
    TaskEvent.add(
        actor="assistant",
        action="fetch_sentry_issues",
        target=project_slug,
        message=f"Fetched {len(issues)} issues for project '{project_slug}'",
    )
    if issues:
        assembled_issues = "---\n"
        for issue in issues:
            assembled_issues += f"Title: {issue['title']}\n"
            assembled_issues += f"URL: {issue['permalink']}\n"
            assembled_issues += f"Status: {issue['status']}\n"
            assembled_issues += f"---\n"
        return f"Found {len(issues)} issues for project '{project_slug}':\n\n{assembled_issues}"
    else:
        return f"No issues found for project '{project_slug}'."


def create_sentry_issue(api_key: str, project_slug: str, title: str, description: str) -> str:
    url = f"https://sentry.io/api/0/projects/{project_slug}/issues/"
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {"title": title, "description": description}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 201:
        raise SentryAPIError(f"Error creating Sentry issue: {response.status_code}")
    issue = response.json()
    TaskEvent.add(
        actor="assistant",
        action="create_sentry_issue",
        target=project_slug,
        message=f"Created issue '{title}' for project '{project_slug}'",
    )
    return f"Issue '{title}' created successfully: {issue['permalink']}"


# Define a schema for the input parameters
class CreateSentryIssueInput(BaseModel):
    project_slug: str = Field(..., title="Sentry project slug")
    title: str = Field(..., title="Title of the issue")
    description: str = Field(..., title="Description of the issue")


FETCH_ISSUES_TOOL_DESCRIPTION = """
Fetch issues from a Sentry project.
"""


CREATE_ISSUE_TOOL_DESCRIPTION = """
Create a new issue in a Sentry project.
"""


def list_sentry_tools(api_key: str) -> list:
    fetch_issues_tool = Tool(
        name="fetch_sentry_issues",
        func=lambda project_slug: fetch_sentry_issues(api_key, project_slug),
        description=FETCH_ISSUES_TOOL_DESCRIPTION,
    )

    create_issue_tool = StructuredTool(
        name="create_sentry_issue",
        func=lambda project_slug, title, description: create_sentry_issue(
            api_key, project_slug, title, description
        ),
        description=CREATE_ISSUE_TOOL_DESCRIPTION,
        args_schema=CreateSentryIssueInput,
    )

    return [fetch_issues_tool, create_issue_tool]
