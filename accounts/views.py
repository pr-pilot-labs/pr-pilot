import json

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt


# Create your views here.

def user_profile(request):
    # Check if the user is authenticated
    if request.user.is_authenticated:
        # Pass the user object to the template
        return render(request, 'user_profile.html', {'user': request.user})
    else:
        # If the user is not authenticated, redirect to login page or show an error
        return render(request, 'accounts/login_error.html')

def home(request):
    if request.user.is_authenticated:
        # Redirect to dashboard
        return redirect('task_list')
    else:
        return render(request, 'home.html')


def health_check(request):
    return HttpResponse("OK")