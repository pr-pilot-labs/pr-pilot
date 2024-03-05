import logging
import re

from django.http import JsonResponse
from github import Github

from engine.models import Task
from webhooks.jwt_tools import get_installation_access_token

logger = logging.getLogger(__name__)


def handle_pull_request_review_comment(payload):
    # Extract commenter's username
    commenter_username = payload['comment']['user']['login']
    comment_id = payload['comment']['id']
    pr_number = payload['pull_request']['number']
    head = payload['pull_request']['head']['ref']
    base = payload['pull_request']['base']['ref']
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
        comment = repo.get_pull(pr_number).get_comment(comment_id)
        comment.create_reaction("eyes")
        user_request = f"""
    The Github user `{commenter_username}` mentioned you in a pull request:
    PR number: {pr_number}
    User Comment:
    ```
    {command}
    ```

    Read the pull request, fulfill the user's request and return the response to the user's comment.
    """
        Task.schedule(title=command, user_request=user_request, comment_id=comment_id,
                      pr_number=pr_number, head=head, base=base,
                      installation_id=installation_id, github_project=repository,
                      github_user=commenter_username, branch="main")

    else:
        command = None

    return JsonResponse({'status': 'ok', 'message': 'PR comment processed'})
