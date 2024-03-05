import json

from django.shortcuts import render
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
