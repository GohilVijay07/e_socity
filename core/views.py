from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, PasswordResetCompleteView, PasswordResetDoneView
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db.models import Q, Sum
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
import random
from .forms import UserSignupForm, UserLoginForm, UserProfileForm, ContactForm, StrictPasswordResetForm
from .models import User
from socity.models import Resident

# Create your views here.
def home(request):
    """Home page view"""
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    """User dashboard view - Role-based feature display"""
    context = {
        'user_role': request.user.role,
    }
    return render(request, 'core/dashboard.html', context)

def userSignupView(request):
    if request.user.is_authenticated:
        return redirect('home')  # Redirect to home if already logged in
    
    if request.method == "POST":
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Send welcome email
            if user.email:
                try:
                    print(f"\n📧 Sending welcome email to {user.email}...")
                    # Render HTML email template
                    html_content = render_to_string('core/emails/welcome_email.html', {
                        'user_name': user.get_full_name() or user.username,
                        'user_email': user.email,
                        'user_role': user.get_role_display(),
                        'login_time': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
                        'dashboard_url': request.build_absolute_uri('/dashboard/'),
                    })
                    
                    # Create email with HTML content
                    email = EmailMultiAlternatives(
                        subject='Welcome to e_socity',
                        body='Welcome! Your account has been created successfully.',
                        from_email=settings.EMAIL_HOST_USER,
                        to=[user.email],
                    )
                    email.attach_alternative(html_content, "text/html")
                    email.send(fail_silently=False)
                    print(f"✅ Welcome email sent successfully to {user.email}")
                    messages.success(request, 'Account created! Welcome email sent.')
                except Exception as exc:
                    print(f"❌ Email Error: {exc}")
                    messages.warning(request, f'Account created but email could not be sent.')
            
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
        login_data = request.POST.copy()
        identifier = (login_data.get('username') or login_data.get('email') or '').strip()
        if identifier:
            login_data['username'] = identifier

        form = UserLoginForm(request, data=login_data)
        if form.is_valid():
            username = (form.cleaned_data.get('username') or '').strip()
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

def contact_view(request):
    """Contact form view"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data.get('name')
            email = form.cleaned_data.get('email')
            subject = form.cleaned_data.get('subject')
            message = form.cleaned_data.get('message')
            
            # Send email to admin
            admin_email = settings.EMAIL_HOST_USER
            
            try:
                # Render HTML email template
                html_content = render_to_string('core/emails/contact_email.html', {
                    'sender_name': name,
                    'sender_email': email,
                    'subject': subject,
                    'message': message,
                    'timestamp': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
                })
                
                # Create email with HTML content
                email_msg = EmailMultiAlternatives(
                    subject=f"Contact Form: {subject}",
                    body=f"From: {name} ({email})\n\nMessage:\n{message}",
                    from_email=settings.EMAIL_HOST_USER,
                    to=[admin_email],
                )
                email_msg.attach_alternative(html_content, "text/html")
                email_msg.send(fail_silently=False)
                
                messages.success(request, 'Your message has been sent successfully!')
                return redirect('home')
            except Exception as exc:
                messages.error(request, f'Failed to send message: {exc}')
    else:
        form = ContactForm()
    
    return render(request, 'core/contact.html', {'form': form})


def password_reset_otp_request_view(request):
    if request.method == 'POST':
        form = StrictPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            otp = f"{random.randint(100000, 999999)}"
            expiry = timezone.now() + timedelta(minutes=10)

            request.session['reset_email'] = email
            request.session['reset_otp'] = otp
            request.session['reset_otp_expiry'] = expiry.isoformat()

            try:
                html_content = render_to_string('core/emails/password_reset_otp_email.html', {
                    'otp': otp,
                    'expiry_minutes': 10,
                })
                email_msg = EmailMultiAlternatives(
                    subject='e_socity Password Reset OTP',
                    body=f'Your OTP is {otp}. It is valid for 10 minutes.',
                    from_email=settings.EMAIL_HOST_USER,
                    to=[email],
                )
                email_msg.attach_alternative(html_content, 'text/html')
                email_msg.send(fail_silently=False)
            except Exception:
                messages.error(request, 'OTP email could not be sent. Please try again.')
                return render(request, 'core/password_reset.html', {'form': form})

            messages.success(request, 'OTP sent to your email address.')
            return redirect('password_reset_otp_verify')
    else:
        form = StrictPasswordResetForm()

    return render(request, 'core/password_reset.html', {'form': form})


def password_reset_otp_verify_view(request):
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, 'Please request OTP first.')
        return redirect('password_reset')

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        saved_otp = request.session.get('reset_otp')
        expiry_raw = request.session.get('reset_otp_expiry')

        if not saved_otp or not expiry_raw:
            messages.error(request, 'OTP session expired. Please request a new OTP.')
            return redirect('password_reset')

        expiry = timezone.datetime.fromisoformat(expiry_raw)
        if timezone.is_naive(expiry):
            expiry = timezone.make_aware(expiry, timezone.get_current_timezone())

        if timezone.now() > expiry:
            messages.error(request, 'OTP has expired. Please request a new OTP.')
            return redirect('password_reset')

        if otp != saved_otp:
            messages.error(request, 'Invalid OTP. Please try again.')
            return render(request, 'core/otp_verify.html')

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'core/otp_verify.html')

        try:
            validate_password(new_password)
        except ValidationError as exc:
            for message in exc.messages:
                messages.error(request, message)
            return render(request, 'core/otp_verify.html')

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            messages.error(request, 'User not found for this email.')
            return redirect('password_reset')

        user.set_password(new_password)
        user.save()

        for key in ['reset_email', 'reset_otp', 'reset_otp_expiry']:
            request.session.pop(key, None)

        messages.success(request, 'Password reset successful. Please login with your new password.')
        return redirect('login')

    return render(request, 'core/otp_verify.html')


# Django Built-in Password Reset Views (Link-based)
class CustomPasswordResetView(PasswordResetView):
    form_class = StrictPasswordResetForm
    template_name = 'core/password_reset.html'
    email_template_name = 'core/password_reset_email.html'
    html_email_template_name = 'core/password_reset_email.html'
    subject_template_name = 'core/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    
    def form_valid(self, form):
        print(f"\n📧 PASSWORD RESET REQUESTED")
        print(f"Email: {form.cleaned_data['email']}")
        print(f"Sending password reset email...\n")
        return super().form_valid(form)


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'core/password_reset_done.html'


# ============= ERROR HANDLERS =============

def error_403(request, exception=None):
    """Handle 403 Forbidden errors"""
    return render(request, '403.html', {'user_role': request.user.role if request.user.is_authenticated else None}, status=403)


def error_404(request, exception=None):
    """Handle 404 Not Found errors"""
    return render(request, '404.html', status=404)


def error_500(request):
    """Handle 500 Server errors"""
    return render(request, '500.html', status=500)
class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'core/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'core/password_reset_complete.html'