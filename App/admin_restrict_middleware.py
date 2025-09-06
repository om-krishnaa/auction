# your_app/middleware/admin_restrict_middleware.py

from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the path starts with /admin/
        if request.path.startswith('/arjun/admin/'):
            # If the user is not authenticated or not staff
            if not (request.user.is_authenticated and request.user.user_type == "admin"):
                return HttpResponseForbidden("You are not authorized to access the admin panel.")
                # Or use this to redirect:
                # return redirect(reverse('login'))  # or any other page

        return self.get_response(request)
