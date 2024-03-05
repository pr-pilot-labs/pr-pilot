import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from github import Github

from accounts.models import GitHubAppInstallation, GitHubRepository, GitHubAccount


# Create your views here.

def user_profile(request):
    # Check if the user is authenticated
    if request.user.is_authenticated:
        # Pass the user object to the template
        return render(request, 'user_profile.html', {'user': request.user})
    else:
        # If the user is not authenticated, redirect to login page or show an error
        return render(request, 'accounts/login_error.html')


def is_valid_signature(request):
    github_signature = request.headers.get('X-Hub-Signature-256')
    if not github_signature:
        return False
    signature = 'sha256=' + hmac.new(
        bytes(settings.GITHUB_WEBHOOK_SECRET, 'utf-8'),
        msg=request.body,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(github_signature, signature)

@csrf_exempt
def github_webhook(request):
    if request.method == 'POST':
        payload = json.loads(request.body.decode('utf-8'))
        if payload['action'] == 'created':
            # Parse account data
            account_data = payload['installation']['account']
            account, _ = GitHubAccount.objects.get_or_create(
                account_id=account_data['id'],
                defaults={
                    'login': account_data['login'],
                    'avatar_url': account_data['avatar_url'],
                    'html_url': account_data['html_url'],
                }
            )

            # Parse installation data
            installation_data = payload['installation']
            installation, _ = GitHubAppInstallation.objects.update_or_create(
                installation_id=installation_data['id'],
                app_id=installation_data['app_id'],
                target_id=installation_data['target_id'],
                target_type=installation_data['target_type'],
                defaults={
                    'account': account,
                    'access_tokens_url': installation_data['access_tokens_url'],
                    'repositories_url': installation_data['repositories_url'],
                    'installed_at': parse_datetime(installation_data['created_at']),
                }
            )
            return JsonResponse({'status': 'success', 'installation_id': installation.installation_id})
        elif payload['action'] == 'deleted':
            # Handle uninstallation
            GitHubAppInstallation.objects.filter(installation_id=payload['installation']['id']).delete()
            return JsonResponse({'status': 'success', 'message': 'Installation deleted'})
        else:
            return JsonResponse({'status': 'ignored', 'message': 'No action taken'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


def get_user_repositories(user):
    installations = GitHubAppInstallation.objects.filter(account__login=user.username)
    repositories = []
    for installation in installations:
        g = Github(installation.access_token)
        repositories.extend(g.get_user().get_repos())
    return repositories

def repository_permissions(request):
    repositories = get_user_repositories(request.user)
    return render(request, 'permissions.html', {'repositories': repositories})