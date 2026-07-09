from django.shortcuts import redirect
from functools import wraps

def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login') # Replace 'login' with your login route name when it exists
            
            # Check if user has a UserProfile and the correct role
            if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != role:
                return redirect('login')
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
