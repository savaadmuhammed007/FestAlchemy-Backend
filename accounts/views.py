from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required

# Instead of custom manual login views, we'll rely on the default django.contrib.auth.views mapped in urls.py
# We just need a dashboard redirector to handle the routing per role.

@login_required
def dashboard_redirect(request):
    if not hasattr(request.user, 'userprofile'):
        return redirect('home')
        
    role = request.user.userprofile.role
    if role == 'admin':
        return redirect('admin_dashboard')
    elif role == 'teamlead':
        return redirect('teamlead_dashboard')
    elif role == 'judge':
        return redirect('judge_dashboard')
        
    return redirect('home')

def signup(request):
    from django.contrib.auth.forms import UserCreationForm
    from .models import UserProfile
    from django.contrib import messages
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user, role='user') # default role
            messages.success(request, 'Account created successfully! You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
        
    return render(request, 'accounts/signup.html', {'form': form})
