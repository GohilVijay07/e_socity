"""
Role-based access control decorators for e-Society Management System
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def _raise_forbidden(message):
    """Raise a 403 with a consistent UX message."""
    raise PermissionDenied(message)


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
                _raise_forbidden('You do not have permission to access this page.')
            
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
                _raise_forbidden('You do not have permission to access this page.')
            
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
            _raise_forbidden('Only administrators can access this page.')
        
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
            _raise_forbidden('Only residents can access this page.')
        
        # Profile setup issue is not an authorization issue.
        # Redirect with guidance instead of returning 403.
        try:
            request.user.resident_profile
        except Exception:
            messages.error(request, 'Resident profile not found. Please contact admin to assign your unit/profile.')
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
            _raise_forbidden('Only staff members can access this page.')
        
        # Profile setup issue is not an authorization issue.
        # Redirect with guidance instead of returning 403.
        try:
            request.user.staff_profile
        except Exception:
            messages.error(request, 'Staff profile not found. Please contact admin to create your staff profile.')
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
            _raise_forbidden('This page is for visitors only.')
        
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
            _raise_forbidden('You do not have permission to access this page.')
        
        return view_func(request, *args, **kwargs)
    return wrapper
