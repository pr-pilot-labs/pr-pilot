from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of paths that don't require authentication
        open_paths = [
            reverse('account_login'),
            reverse('account_logout'),
            reverse('home'),
            reverse('github_webhook'),
            '/accounts/github/login/',
            '/accounts/github/login/callback/',
        ]

        if not request.user.is_authenticated and request.path not in open_paths:
            return redirect('/')  # Redirect to the login page

        response = self.get_response(request)
        return response