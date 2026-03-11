"""
Role-based access control decorators for e-Society Management System
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden


def role_required(required_role):
    """
    Decorator to check if user has required role
    Usage: @role_required('ADMIN')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Please login first.')
                return redirect('login')
            
            if request.user.role != required_role:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def multiple_roles_required(*roles):
    """
    Decorator to check if user has one of the required roles
    Usage: @multiple_roles_required('ADMIN', 'STAFF')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Please login first.')
                return redirect('login')
            
            if request.user.role not in roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """Decorator to restrict access to admins only"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login first.')
            return redirect('login')
        
        if request.user.role != 'ADMIN':
            messages.error(request, 'Only administrators can access this page.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def resident_required(view_func):
    """Decorator to restrict access to residents only"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login first.')
            return redirect('login')
        
        if request.user.role != 'RESIDENT':
            messages.error(request, 'Only residents can access this page.')
            return redirect('dashboard')
        
        # Check if resident has a resident profile
        try:
            resident = request.user.resident_profile
        except:
            messages.error(request, 'Resident profile not found.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_required(view_func):
    """Decorator to restrict access to staff only"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login first.')
            return redirect('login')
        
        if request.user.role != 'STAFF':
            messages.error(request, 'Only staff members can access this page.')
            return redirect('dashboard')
        
        # Check if staff has a staff profile
        try:
            staff = request.user.staff_profile
        except:
            messages.error(request, 'Staff profile not found.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def visitor_required(view_func):
    """Decorator to restrict access to visitors only"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login first.')
            return redirect('login')
        
        if request.user.role != 'VISITOR':
            messages.error(request, 'This page is for visitors only.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_or_admin_required(view_func):
    """Decorator for pages accessible to both staff and admins"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login first.')
            return redirect('login')
        
        if request.user.role not in ['ADMIN', 'STAFF']:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper
