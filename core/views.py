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
from django.core.paginator import Paginator
from datetime import timedelta
import random
from .forms import UserSignupForm, UserLoginForm, UserProfileForm, ContactForm, StrictPasswordResetForm
from .models import User, EmailVerificationToken, Notification
from socity.models import Resident
from .services import send_email_verification, create_notification, ensure_user_role_setup


def get_dashboard_route_for_user(user):
    if user.is_superuser or user.role == 'ADMIN':
        return 'socity:admin_dashboard_login_redirect'
    if user.role == 'RESIDENT':
        if not Resident.objects.filter(user=user).exists():
            return None
        return 'socity:resident_dashboard_login_redirect'
    if user.role == 'STAFF':
        if not hasattr(user, 'staff_profile'):
            return None
        return 'socity:staff_dashboard_login_redirect'
    return None

# Create your views here.
def home(request):
    """Home page view"""
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    """Central dashboard route that redirects users to role-specific dashboards."""
    role_dashboard_route = get_dashboard_route_for_user(request.user)
    if role_dashboard_route:
        return redirect(role_dashboard_route)

    has_resident_profile = Resident.objects.filter(user=request.user).exists()
    has_staff_profile = hasattr(request.user, 'staff_profile')

    context = {
        'user_role': request.user.role,
        'has_resident_profile': has_resident_profile,
        'has_staff_profile': has_staff_profile,
    }

    if request.user.role == 'RESIDENT' and not has_resident_profile:
        messages.info(request, 'Your resident profile is not assigned yet. Please contact admin.')
        dedupe_since = timezone.now() - timedelta(hours=6)
        pending_message_key = request.user.username
        already_notified = Notification.objects.filter(
            user__role='ADMIN',
            title='Resident Profile Pending Assignment',
            message__icontains=pending_message_key,
            created_at__gte=dedupe_since,
        ).exists()
        if not already_notified:
            for admin_user in User.objects.filter(role='ADMIN', is_active=True):
                create_notification(
                    admin_user,
                    title='Resident Profile Pending Assignment',
                    message=(
                        f'Resident user {request.user.get_full_name() or request.user.username} '
                        f'({request.user.email or request.user.username}) needs unit/profile assignment.'
                    ),
                    notification_type='WARNING',
                    action_url='/management/users/',
                    send_email=True,
                    email_subject='Resident Profile Assignment Needed',
                )
    if request.user.role == 'STAFF' and not has_staff_profile:
        messages.info(request, 'Your staff profile is not assigned yet. Please contact admin.')
        dedupe_since = timezone.now() - timedelta(hours=6)
        pending_message_key = request.user.username
        already_notified = Notification.objects.filter(
            user__role='ADMIN',
            title='Staff Profile Pending Assignment',
            message__icontains=pending_message_key,
            created_at__gte=dedupe_since,
        ).exists()
        if not already_notified:
            for admin_user in User.objects.filter(role='ADMIN', is_active=True):
                create_notification(
                    admin_user,
                    title='Staff Profile Pending Assignment',
                    message=(
                        f'Staff user {request.user.get_full_name() or request.user.username} '
                        f'({request.user.email or request.user.username}) needs staff profile assignment.'
                    ),
                    notification_type='WARNING',
                    action_url='/management/staff/',
                    send_email=True,
                    email_subject='Staff Profile Assignment Needed',
                )

    return render(request, 'core/dashboard.html', context)

def userSignupView(request):
    if request.user.is_authenticated:
        return redirect('home')  # Redirect to home if already logged in

    if request.method == "POST":
        form = UserSignupForm(request.POST)
        if form.is_valid():
            otp = f"{random.randint(100000, 999999)}"
            expiry = timezone.now() + timedelta(minutes=10)
            payload = {
                'email': form.cleaned_data['email'],
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'gender': form.cleaned_data.get('gender') or '',
                'phone': form.cleaned_data.get('phone') or '',
                'role': form.cleaned_data['role'],
                'password': form.cleaned_data['password1'],
            }

            request.session['signup_payload'] = payload
            request.session['signup_otp'] = otp
            request.session['signup_otp_expiry'] = expiry.isoformat()
            request.session.modified = True

            try:
                html_content = render_to_string('core/emails/signup_otp_email.html', {
                    'user_name': f"{payload['first_name']} {payload['last_name']}".strip() or payload['email'],
                    'otp': otp,
                    'expiry_minutes': 10,
                })
                email_msg = EmailMultiAlternatives(
                    subject='e-Socity Signup OTP',
                    body=f'Your signup OTP is {otp}. It is valid for 10 minutes.',
                    from_email=settings.EMAIL_HOST_USER,
                    to=[payload['email']],
                )
                email_msg.attach_alternative(html_content, 'text/html')
                email_msg.send(fail_silently=False)
            except Exception:
                for key in ['signup_payload', 'signup_otp', 'signup_otp_expiry']:
                    request.session.pop(key, None)
                messages.error(request, 'OTP email could not be sent. Please try again.')
                return render(request, 'core/signup.html', {'form': form})

            masked_email = payload['email']
            if '@' in masked_email:
                local, domain = masked_email.split('@', 1)
                local = (local[:2] + '*' * max(len(local) - 2, 1)) if len(local) > 2 else (local[:1] + '*')
                masked_email = f'{local}@{domain}'

            messages.success(request, f'OTP sent to {masked_email}. Verify OTP to complete signup.')
            return redirect('signup_otp_verify')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserSignupForm()
    
    return render(request, 'core/signup.html', {'form': form})


def signup_otp_verify_view(request):
    payload = request.session.get('signup_payload')
    if not payload:
        messages.error(request, 'Please fill signup form first.')
        return redirect('signup')

    if request.method == 'POST':
        action = (request.POST.get('action') or 'verify').strip()

        if action == 'resend':
            otp = f"{random.randint(100000, 999999)}"
            expiry = timezone.now() + timedelta(minutes=10)
            request.session['signup_otp'] = otp
            request.session['signup_otp_expiry'] = expiry.isoformat()
            request.session.modified = True

            try:
                html_content = render_to_string('core/emails/signup_otp_email.html', {
                    'user_name': f"{payload.get('first_name', '')} {payload.get('last_name', '')}".strip() or payload.get('email', ''),
                    'otp': otp,
                    'expiry_minutes': 10,
                })
                email_msg = EmailMultiAlternatives(
                    subject='e-Socity Signup OTP',
                    body=f'Your signup OTP is {otp}. It is valid for 10 minutes.',
                    from_email=settings.EMAIL_HOST_USER,
                    to=[payload.get('email')],
                )
                email_msg.attach_alternative(html_content, 'text/html')
                email_msg.send(fail_silently=False)
            except Exception:
                messages.error(request, 'Unable to resend OTP right now. Please try again.')
                return redirect('signup_otp_verify')

            messages.success(request, 'A new OTP has been sent to your email.')
            return redirect('signup_otp_verify')

        otp = (request.POST.get('otp') or '').strip()
        saved_otp = request.session.get('signup_otp')
        expiry_raw = request.session.get('signup_otp_expiry')

        if not saved_otp or not expiry_raw:
            messages.error(request, 'OTP session expired. Please signup again.')
            return redirect('signup')

        expiry = timezone.datetime.fromisoformat(expiry_raw)
        if timezone.is_naive(expiry):
            expiry = timezone.make_aware(expiry, timezone.get_current_timezone())

        if timezone.now() > expiry:
            messages.error(request, 'OTP has expired. Please request a new OTP.')
            return redirect('signup_otp_verify')

        if otp != saved_otp:
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('signup_otp_verify')

        if User.objects.filter(email__iexact=payload.get('email', '')).exists():
            for key in ['signup_payload', 'signup_otp', 'signup_otp_expiry']:
                request.session.pop(key, None)
            messages.error(request, 'This email is already registered. Please login.')
            return redirect('login')

        signup_form = UserSignupForm({
            'email': payload.get('email', ''),
            'first_name': payload.get('first_name', ''),
            'last_name': payload.get('last_name', ''),
            'gender': payload.get('gender', ''),
            'phone': payload.get('phone', ''),
            'role': payload.get('role', 'RESIDENT'),
            'password1': payload.get('password', ''),
            'password2': payload.get('password', ''),
        })

        if not signup_form.is_valid():
            for key in ['signup_payload', 'signup_otp', 'signup_otp_expiry']:
                request.session.pop(key, None)
            messages.error(request, 'Signup details are invalid or expired. Please fill signup form again.')
            return redirect('signup')

        user = signup_form.save()

        setup_result = ensure_user_role_setup(user)
        for admin_user in User.objects.filter(role='ADMIN', is_active=True):
            if setup_result.get('resident_created'):
                create_notification(
                    admin_user,
                    title='New Resident Auto-Onboarded',
                    message=(
                        f'{user.get_full_name() or user.username} signed up as Resident and was auto-assigned '
                        f'to unit {setup_result.get("unit_assigned")}. '
                        f'{"New auto unit created." if setup_result.get("unit_auto_created") else ""}'
                    ),
                    notification_type='INFO',
                    action_url='/management/residents/',
                    send_email=True,
                    email_subject='New Resident Auto-Onboarded',
                )
            elif setup_result.get('staff_created'):
                create_notification(
                    admin_user,
                    title='New Staff Auto-Onboarded',
                    message=f'{user.get_full_name() or user.username} signed up as Staff and profile was auto-created.',
                    notification_type='INFO',
                    action_url='/management/staff/',
                    send_email=True,
                    email_subject='New Staff Auto-Onboarded',
                )
            elif user.role == 'VISITOR':
                create_notification(
                    admin_user,
                    title='New Visitor Signup',
                    message=f'{user.get_full_name() or user.username} signed up as Visitor.',
                    notification_type='INFO',
                    action_url='/management/users/',
                    send_email=True,
                    email_subject='New Visitor Signup',
                )

        if user.email:
            try:
                send_email_verification(user, request)
                messages.info(request, 'A verification link has been sent to your email.')
            except Exception:
                messages.warning(request, 'Verification email could not be sent right now. You can resend it after login.')

        if user.email:
            try:
                html_content = render_to_string('core/emails/welcome_email.html', {
                    'user_name': user.get_full_name() or user.username,
                    'user_email': user.email,
                    'user_role': user.get_role_display(),
                    'login_time': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
                    'dashboard_url': request.build_absolute_uri('/dashboard/'),
                })

                email = EmailMultiAlternatives(
                    subject='Welcome to e_socity',
                    body='Welcome! Your account has been created successfully.',
                    from_email=settings.EMAIL_HOST_USER,
                    to=[user.email],
                )
                email.attach_alternative(html_content, "text/html")
                email.send(fail_silently=False)
            except Exception:
                messages.warning(request, 'Account created but welcome email could not be sent.')

        for key in ['signup_payload', 'signup_otp', 'signup_otp_expiry']:
            request.session.pop(key, None)

        messages.success(request, 'Account created successfully! Please login to continue.')
        return redirect('login')

    masked_email = payload.get('email', '')
    if '@' in masked_email:
        local, domain = masked_email.split('@', 1)
        local = (local[:2] + '*' * max(len(local) - 2, 1)) if len(local) > 2 else (local[:1] + '*')
        masked_email = f'{local}@{domain}'

    return render(request, 'core/signup_otp_verify.html', {'masked_email': masked_email})

def userLoginView(request):
    if request.user.is_authenticated:
        role_dashboard_route = get_dashboard_route_for_user(request.user)
        if role_dashboard_route:
            return redirect(role_dashboard_route)
        return redirect('dashboard')
    
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
                if not user.email_verified:
                    messages.warning(request, 'Your email is not verified yet. Please verify to secure your account.')
                role_dashboard_route = get_dashboard_route_for_user(user)
                if role_dashboard_route:
                    return redirect(role_dashboard_route)
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


def email_verify_view(request, token):
    """Verify user email using a one-time token link."""
    token_obj = EmailVerificationToken.objects.select_related('user').filter(token=token).first()
    if not token_obj:
        messages.error(request, 'Invalid verification link.')
        return redirect('login')

    if not token_obj.is_valid():
        messages.error(request, 'Verification link has expired or was already used.')
        return redirect('login')

    user = token_obj.user
    user.email_verified = True
    user.save(update_fields=['email_verified'])
    token_obj.is_used = True
    token_obj.save(update_fields=['is_used'])

    messages.success(request, 'Email verified successfully. You can now continue securely.')
    return redirect('login')


@login_required
def resend_verification_email_view(request):
    """Resend verification email for currently logged-in user."""
    if request.user.email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('dashboard')

    try:
        send_email_verification(request.user, request)
        messages.success(request, 'Verification email sent. Please check your inbox.')
    except Exception:
        messages.error(request, 'Unable to send verification email right now. Please try later.')
    return redirect('dashboard')


@login_required
def notifications_view(request):
    """In-app notification inbox for current user."""
    notifications_qs = Notification.objects.filter(user=request.user).order_by('-created_at')
    notif_filter = (request.GET.get('filter') or 'all').strip().lower()

    filter_map = {
        'complaint': ['complaint'],
        'billing': ['bill', 'billing', 'payment'],
        'visitor': ['visitor', 'entry', 'gate'],
        'amenity': ['amenity', 'booking'],
        'staff': ['staff', 'task', 'assigned'],
        'account': ['email', 'verification', 'password', 'account', 'profile'],
    }

    if notif_filter in filter_map:
        query = Q()
        for keyword in filter_map[notif_filter]:
            query |= Q(title__icontains=keyword) | Q(message__icontains=keyword)
        notifications_qs = notifications_qs.filter(query)
    else:
        notif_filter = 'all'

    # Keep staff notification UX minimal: only All and Staff buckets.
    if request.user.role == 'STAFF':
        if notif_filter not in ['all', 'staff']:
            notif_filter = 'all'
        if notif_filter == 'staff':
            staff_query = Q()
            for keyword in filter_map['staff']:
                staff_query |= Q(title__icontains=keyword) | Q(message__icontains=keyword)
            notifications_qs = notifications_qs.filter(staff_query)

    paginator = Paginator(notifications_qs, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'core/notifications.html', {'page_obj': page_obj, 'notif_filter': notif_filter})


@login_required
def notification_read_view(request, notification_id):
    """Mark a single notification as read."""
    note = get_object_or_404(Notification, id=notification_id, user=request.user)
    if request.method == 'POST':
        note.is_read = True
        note.save(update_fields=['is_read'])
        if note.action_url:
            return redirect(note.action_url)
    return redirect('notifications')


@login_required
def notifications_mark_all_read_view(request):
    """Mark all notifications as read for current user."""
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notifications')


@login_required
def profile_view(request):
    """View current user's profile details."""
    resident = Resident.objects.filter(user=request.user).select_related('unit').first()
    return render(request, 'core/profile.html', {'resident': resident, 'user': request.user})


@login_required
def profile_edit(request):
    """Edit user profile including image upload."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile_view')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'core/profile_edit.html', {'form': form})


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