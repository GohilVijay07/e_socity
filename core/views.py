from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from .forms import UserSignupForm, UserLoginForm, UserProfileForm
from socity.models import Resident

# Create your views here.
def home(request):
    """Home page view"""
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    """User dashboard view"""
    return render(request, 'core/dashboard.html')

def userSignupView(request):
    if request.user.is_authenticated:
        return redirect('home')  # Redirect to home if already logged in
    
    if request.method == "POST":
        form = UserSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully! Please login to continue.')
            return redirect('login')  # Redirect to login page after successful signup
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserSignupForm()
    
    return render(request, 'core/signup.html', {'form': form})

def userLoginView(request):
    if request.user.is_authenticated:
        return redirect('home')  # Redirect to home if already logged in
    
    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'core/login.html', {'form': form})

def userLogoutView(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')
