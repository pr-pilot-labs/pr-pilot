import logging
import re

from django.http import JsonResponse
from github import Github

from engine.models import Task
from webhooks.jwt_tools import get_installation_access_token

logger = logging.getLogger(__name__)


def handle_issue_comment(payload: dict):
    # Extract commenter's username
    commenter_username = payload['comment']['user']['login']
    issue_number = payload['issue']['number']
    repository = payload['repository']['full_name']
    installation_id = payload['installation']['id']

    # Extract comment text
    comment_text = payload['comment']['body']

    # Look for slash command pattern
    match = re.search(r'/pilot\s+(.+)', comment_text)

    # If a slash command is found, extract the command
    if match:
        command = match.group(1)
        logger.info(f'Found command: {command} by {commenter_username}')
        g = Github(get_installation_access_token(installation_id))
        repo = g.get_repo(repository)
        # Get the issue
        issue = repo.get_issue(number=issue_number)
        # Create a comment mentioning the user with the command
        issue.create_comment(f'@{commenter_username} Hang tight, I\'ll take a look')
        user_request = f"""
The Github user `{commenter_username}` requested the following command:

```
{command}
```

Issue number: {issue_number}

Read the issue, fulfill the user's request and post the result as a comment.
"""
        Task.schedule(title="Respond to comment", user_request=user_request,
                      installation_id=installation_id, github_project=repository,
                      github_user=commenter_username, branch="main")

    else:
        command = None

    return JsonResponse({'status': 'ok', 'message': 'Issue comment processed'})
