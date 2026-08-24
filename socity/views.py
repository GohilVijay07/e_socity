"""
Role-based Views for e-Society Management System
Handles all views for Admin, Resident, Staff, and Visitor functionalities
"""
from django.shortcuts import render as django_render, redirect as django_redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum
from django.db import transaction
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone
from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.template.loader import get_template
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import random
import json
from io import BytesIO
import csv
from urllib.parse import urlencode

from core.decorators import (
    role_required, admin_required, resident_required, 
    staff_required, multiple_roles_required
)
from core.models import User
from core.services import create_notification, ensure_user_role_setup
from .models import (
    Unit, Resident, Staff, MaintenanceBill, Visitor, Complaint, 
    Amenity, AmenityBooking, Notice, NoticeRecipient, Transaction, Building,
    Task, VisitorApproval, ComplaintUpdate
)
from .forms import (
    ResidentForm, StaffForm, UnitForm, BuildingForm, MaintenanceBillForm,
    NoticeForm, AmenityForm, AmenityBookingApprovalForm, ComplaintStatusForm,
    ComplaintForm, AmenityBookingForm, PaymentForm, VisitorApprovalForm,
    ResidentProfileForm, TaskForm, TaskUpdateForm, VisitorRegistrationForm,
    VisitorExitForm, ComplaintUpdateForm, AdminResidentCreateForm,
    AdminStaffCreateForm, AdminUserCreateForm, AdminUserUpdateForm,
    AdminComplaintUpdateForm, VisitorApprovalActionForm
)


CORE_ROUTE_NAMES = {
    'home',
    'login',
    'logout',
    'dashboard',
    'password_reset',
    'password_reset_otp_verify',
    'contact',
}


def redirect(to, *args, **kwargs):
    """Resolve local socity route names even when namespace is omitted."""
    if isinstance(to, str) and ':' not in to and to not in CORE_ROUTE_NAMES:
        try:
            return django_redirect(f'socity:{to}', *args, **kwargs)
        except NoReverseMatch:
            pass
    return django_redirect(to, *args, **kwargs)


def render(request, template_name, context=None, *args, **kwargs):
    """Render a fallback page when a feature template is not available yet."""
    try:
        get_template(template_name)
    except TemplateDoesNotExist:
        fallback_context = dict(context or {})
        fallback_context.setdefault('missing_template', template_name)
        return django_render(request, 'socity/shared/not_implemented.html', fallback_context, *args, **kwargs)
    return django_render(request, template_name, context, *args, **kwargs)


def _normalize_unit_token(value):
    """Normalize unit text for tolerant matching (e.g., A-101, a 101, A101)."""
    return ''.join(ch for ch in (value or '') if ch.isalnum()).upper()


def _resolve_unit_from_input(unit_no):
    """Resolve unit by exact match first, then tolerant wing/unit matching."""
    raw = (unit_no or '').strip()
    if not raw:
        return None

    exact = Unit.objects.filter(unit_no__iexact=raw).first()
    if exact:
        return exact

    # Common case: user enters a value like "A-101" while unit_no stores only "101".
    # Try explicit wing + unit_no lookup before broad normalized fallback.
    compact = raw.replace(' ', '')
    if '-' in compact:
        wing_part, flat_part = compact.split('-', 1)
        wing = wing_part.strip().upper()
        flat = flat_part.strip()
        if wing and flat:
            wing_match = Unit.objects.filter(wing__iexact=wing, unit_no__iexact=flat).first()
            if wing_match:
                return wing_match

    token = _normalize_unit_token(raw)
    if not token:
        return None

    for unit in Unit.objects.all():
        # Match against multiple canonical forms: unit_no, rendered value (e.g. A-101), and wing+unit_no.
        unit_no_token = _normalize_unit_token(unit.unit_no)
        unit_label_token = _normalize_unit_token(str(unit))
        wing_combo_token = _normalize_unit_token(f"{unit.wing}{unit.unit_no}")
        if token in {unit_no_token, unit_label_token, wing_combo_token}:
            return unit

    return None


def _get_active_host_for_unit(unit):
    """Return an active resident host for a unit if available."""
    if not unit:
        return None
    today = timezone.now().date()
    return (
        Resident.objects.filter(unit=unit, move_in_date__lte=today)
        .filter(Q(move_out_date__isnull=True) | Q(move_out_date__gte=today))
        .select_related('user')
        .order_by('move_in_date')
        .first()
    )


def _get_staff_accessible_complaints(user, staff_profile):
    """Return complaints staff can work on (directly assigned or task-linked)."""
    return (
        Complaint.objects.filter(
            Q(assigned_to=user) | Q(tasks__assigned_to=staff_profile)
        )
        .select_related('raised_by__user', 'assigned_to')
        .distinct()
    )


def _get_visitor_owned_entries(user):
    """Return visitor entries visible to the logged-in visitor only."""
    ownership_filter = Q()
    if user.phone:
        ownership_filter |= Q(phone=user.phone)
    if user.email:
        ownership_filter |= Q(email__iexact=user.email)

    full_name = (user.get_full_name() or '').strip()
    if full_name:
        ownership_filter |= Q(name__iexact=full_name)

    if not ownership_filter:
        return Visitor.objects.none()

    return (
        Visitor.objects.select_related('visit_unit', 'host__user')
        .filter(ownership_filter)
        .order_by('-in_time')
        .distinct()
    )


def _get_visitor_notification_targets(visitor):
    """Find visitor user accounts that should receive approval/rejection notifications."""
    target_filter = Q()
    if visitor.email:
        target_filter |= Q(email__iexact=visitor.email)
    if visitor.phone:
        target_filter |= Q(phone=visitor.phone)

    if not target_filter:
        return User.objects.none()

    return User.objects.filter(role='VISITOR', is_active=True).filter(target_filter).distinct()


def _build_visitor_dashboard_context(request):
    """Build the visitor dashboard context shared by the dashboard and entries pages."""
    visitor_history_filter = Q()
    if request.user.phone:
        visitor_history_filter |= Q(phone=request.user.phone)
    if request.user.email:
        visitor_history_filter |= Q(email__iexact=request.user.email)
    full_name = (request.user.get_full_name() or '').strip()
    if full_name:
        visitor_history_filter |= Q(name__iexact=full_name)

    has_visitor_activity_db = (
        Visitor.objects.filter(visitor_history_filter).exists()
        if visitor_history_filter
        else False
    )
    has_visitor_activity = bool(request.session.get('visitor_has_activity')) or has_visitor_activity_db
    if has_visitor_activity_db and not request.session.get('visitor_has_activity'):
        request.session['visitor_has_activity'] = True

    show_visitor_setup_success = bool(request.session.pop('visitor_setup_completed_once', False))
    base_entries = _get_visitor_owned_entries(request.user)

    search_query = (request.GET.get('search') or '').strip()
    status_filter = (request.GET.get('status') or '').strip()
    approval_filter = (request.GET.get('approval') or '').strip()

    entries = base_entries
    if search_query:
        entries = entries.filter(
            Q(purpose__icontains=search_query)
            | Q(name__icontains=search_query)
            | Q(visit_unit__unit_no__icontains=search_query)
            | Q(visit_unit__wing__icontains=search_query)
            | Q(phone__icontains=search_query)
        )
    if status_filter:
        entries = entries.filter(status=status_filter)
    if approval_filter:
        entries = entries.filter(approval_status=approval_filter)

    total_visits = base_entries.count()
    approved_visits = base_entries.filter(approval_status='APPROVED').count()
    pending_visits = base_entries.filter(approval_status='PENDING').count()
    rejected_visits = base_entries.filter(approval_status='REJECTED').count()

    upcoming_visit = (
        base_entries.filter(status='IN', approval_status__in=['PENDING', 'APPROVED'])
        .order_by('-in_time')
        .first()
    )

    return {
        'show_visitor_info': not has_visitor_activity,
        'show_visitor_setup_success': show_visitor_setup_success,
        'has_visitor_activity': has_visitor_activity,
        'visitor_entries': base_entries,
        'filtered_entries': entries,
        'recent_entries': entries[:25],
        'recent_activity': base_entries[:5],
        'upcoming_visit': upcoming_visit,
        'total_visits': total_visits,
        'approved_visits': approved_visits,
        'pending_visits': pending_visits,
        'rejected_visits': rejected_visits,
        'search_query': search_query,
        'status_filter': status_filter,
        'approval_filter': approval_filter,
        'status_choices': Visitor.STATUS_CHOICES,
        'approval_choices': Visitor.APPROVAL_STATUS_CHOICES,
        'recent_notices': Notice.objects.filter(is_active=True).order_by('-posted_date')[:4],
    }


# ============= ROLE-BASED DASHBOARD =============

@login_required
def dashboard(request):
    """Role-based dashboard view"""
    if request.user.role == 'ADMIN':
        return admin_dashboard(request)
    elif request.user.role == 'RESIDENT':
        return resident_dashboard(request)
    elif request.user.role == 'STAFF':
        return staff_dashboard(request)
    elif request.user.role == 'VISITOR':
        return visitor_dashboard(request)
    else:
        return render(request, 'core/dashboard.html')


@login_required
def visitor_dashboard(request):
    """Visitor dashboard with role context for template rendering."""
    if request.user.role != 'VISITOR':
        messages.error(request, 'This dashboard is available for visitor accounts only.')
        return redirect('dashboard')
    visitor_context = _build_visitor_dashboard_context(request)

    return render(
        request,
        'core/dashboard.html',
        {
            'user_role': request.user.role,
            'has_resident_profile': False,
            'has_staff_profile': False,
            **visitor_context,
        },
    )


@admin_required
def admin_dashboard(request):
    """Admin dashboard with key system statistics."""
    paid_bills = MaintenanceBill.objects.filter(status='PAID').count()
    unpaid_bills = MaintenanceBill.objects.exclude(status='PAID').count()

    # Chart 1: Complaints grouped by status.
    complaint_status_labels = [label for _, label in Complaint.STATUS_CHOICES]
    complaint_status_data = [Complaint.objects.filter(status=key).count() for key, _ in Complaint.STATUS_CHOICES]

    # Chart 2: Monthly maintenance bill payments based on transactions (last 6 months).
    current_month_start = timezone.now().date().replace(day=1)
    month_axis = []
    temp_month = current_month_start
    for _ in range(6):
        month_axis.append(temp_month)
        if temp_month.month == 1:
            temp_month = temp_month.replace(year=temp_month.year - 1, month=12)
        else:
            temp_month = temp_month.replace(month=temp_month.month - 1)
    month_axis.reverse()

    monthly_payment_rows = (
        Transaction.objects.filter(transaction_type='MAINTENANCE')
        .annotate(month=TruncMonth('transaction_date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    monthly_payment_map = {
        row['month'].date().replace(day=1): float(row['total'] or 0)
        for row in monthly_payment_rows
        if row['month']
    }
    monthly_payment_labels = [m.strftime('%b %Y') for m in month_axis]
    monthly_payment_data = [monthly_payment_map.get(m, 0) for m in month_axis]

    # Chart 3: Visitor entries per day (last 7 days).
    day_axis = []
    today = timezone.now().date()
    for delta in range(6, -1, -1):
        day_axis.append(today - timedelta(days=delta))

    visitor_daily_rows = (
        Visitor.objects.filter(in_time__date__gte=day_axis[0])
        .annotate(day=TruncDate('in_time'))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )
    visitor_daily_map = {
        row['day']: int(row['total'] or 0)
        for row in visitor_daily_rows
        if row['day']
    }
    visitor_daily_labels = [d.strftime('%d %b') for d in day_axis]
    visitor_daily_data = [visitor_daily_map.get(d, 0) for d in day_axis]

    context = {
        'total_users': User.objects.filter(role__in=['ADMIN', 'RESIDENT', 'STAFF', 'VISITOR']).count(),
        'total_residents': Resident.objects.count(),
        'total_staff': Staff.objects.count(),
        'total_units': Unit.objects.count(),
        'total_complaints': Complaint.objects.count(),
        'pending_complaints': Complaint.objects.filter(status__in=['OPEN', 'IN_PROGRESS']).count(),
        'total_revenue': Transaction.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0'),
        'paid_bills': paid_bills,
        'unpaid_bills': unpaid_bills,
        'pending_bills': unpaid_bills,
        'visitors_today': Visitor.objects.filter(in_time__date=timezone.now().date()).count(),
        'complaint_status_labels': complaint_status_labels,
        'complaint_status_data': complaint_status_data,
        'monthly_payment_labels': monthly_payment_labels,
        'monthly_payment_data': monthly_payment_data,
        'visitor_daily_labels': visitor_daily_labels,
        'visitor_daily_data': visitor_daily_data,
    }
    return render(request, 'socity/admin/admin_dashboard.html', context)


@resident_required
def resident_dashboard(request):
    """Resident dashboard with personal statistics."""
    try:
        resident = request.user.resident_profile
    except:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')
    
    # Filter bills where the bill is for the resident's move_in_date or later
    # Only show auto-generated bills to residents
    from django.db.models import F, Case, When, DateField
    bills_qs = MaintenanceBill.objects.filter(
        unit=resident.unit,
        is_auto_generated=True,
    ).annotate(
        effective_date=Case(
            When(bill_date__isnull=False, then=F('bill_date')),
            default=F('billing_month'),
            output_field=DateField()
        )
    ).filter(
        effective_date__gte=resident.move_in_date
    ).order_by('-billing_month')
    
    complaints_qs = Complaint.objects.filter(raised_by=resident).order_by('-created_at')
    bookings_qs = AmenityBooking.objects.filter(resident=resident).order_by('-booking_date', '-created_at')
    notices_qs = Notice.objects.filter(is_active=True).order_by('-posted_date')

    context = {
        # Required statistics cards
        'total_bills': bills_qs.count(),
        'pending_bills': bills_qs.exclude(status='PAID').count(),
        'open_complaints': complaints_qs.filter(status__in=['OPEN', 'IN_PROGRESS']).count(),
        'active_bookings': bookings_qs.filter(status__in=['PENDING', 'CONFIRMED']).count(),

        # Backward-compatible values used elsewhere
        'my_bills': bills_qs.count(),
        'my_complaints': complaints_qs.count(),
        'my_bookings': bookings_qs.count(),

        # Dashboard sections
        'my_recent_bills': bills_qs[:5],
        'my_recent_complaints': complaints_qs[:5],
        'my_recent_bookings': bookings_qs[:5],
        'recent_notices': notices_qs[:5],
    }
    return render(request, 'socity/resident/resident_dashboard.html', context)


@staff_required
def staff_dashboard(request):
    """Staff dashboard with operational statistics."""
    try:
        staff = request.user.staff_profile
    except:
        messages.error(request, 'Staff profile not found.')
        return redirect('home')
    
    staff_complaints = _get_staff_accessible_complaints(request.user, staff)

    context = {
        'assigned_complaints': staff_complaints.count(),
        'visitor_entries': Visitor.objects.filter(in_time__date=timezone.now().date()).count(),
        'daily_tasks': Task.objects.filter(assigned_to=staff, status__in=['PENDING', 'IN_PROGRESS']).count(),
        'recent_assigned_complaints': staff_complaints.order_by('-created_at')[:5],
        'recent_visitor_entries': Visitor.objects.order_by('-in_time')[:5],
    }
    return render(request, 'socity/staff/staff_dashboard.html', context)


# ============= ADMIN: RESIDENT MANAGEMENT =============

@admin_required
def search_residents(request):
    """Search residents by name, email, unit, phone, and status."""
    query = (request.GET.get('q') or '').strip()
    residents = Resident.objects.select_related('user', 'unit').all()

    if query:
        residents = residents.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__email__icontains=query)
            | Q(user__phone__icontains=query)
            | Q(unit__unit_no__icontains=query)
            | Q(unit__wing__icontains=query)
            | Q(status__icontains=query)
        )

    context = {
        'query': query,
        'results': residents[:100],
        'result_count': residents.count(),
    }
    return render(request, 'socity/admin/search_residents.html', context)


@admin_required
def search_complaints(request):
    """Search complaints by title, description, resident, category, and status."""
    query = (request.GET.get('q') or '').strip()
    complaints = Complaint.objects.select_related('raised_by__user', 'assigned_to').all()

    if query:
        complaints = complaints.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(category__icontains=query)
            | Q(status__icontains=query)
            | Q(raised_by__user__first_name__icontains=query)
            | Q(raised_by__user__last_name__icontains=query)
            | Q(raised_by__unit__unit_no__icontains=query)
        )

    context = {
        'query': query,
        'results': complaints.order_by('-created_at')[:100],
        'result_count': complaints.count(),
    }
    return render(request, 'socity/admin/search_complaints.html', context)


@admin_required
def search_visitors(request):
    """Search visitors by name, phone, purpose, unit, and status."""
    query = (request.GET.get('q') or '').strip()
    visitors = Visitor.objects.select_related('visit_unit').all()

    if query:
        visitors = visitors.filter(
            Q(name__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
            | Q(purpose__icontains=query)
            | Q(status__icontains=query)
            | Q(approval_status__icontains=query)
            | Q(visit_unit__unit_no__icontains=query)
            | Q(visit_unit__wing__icontains=query)
        )

    context = {
        'query': query,
        'results': visitors.order_by('-in_time')[:100],
        'result_count': visitors.count(),
    }
    return render(request, 'socity/admin/search_visitors.html', context)


# ============= ADMIN: USER MANAGEMENT =============

@admin_required
def user_list(request):
    """List all users with role/status filters."""
    search_query = (request.GET.get('search') or '').strip()
    role_filter = (request.GET.get('role') or '').strip()
    active_filter = (request.GET.get('active') or '').strip()

    users = User.objects.filter(role__in=['ADMIN', 'RESIDENT', 'STAFF', 'VISITOR']).order_by('-date_joined')

    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone__icontains=search_query)
        )
    if role_filter:
        users = users.filter(role=role_filter)
    if active_filter in ['yes', 'no']:
        users = users.filter(is_active=(active_filter == 'yes'))

    paginator = Paginator(users, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'users': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'active_filter': active_filter,
        'role_choices': [
            ('ADMIN', 'Administrator'),
            ('RESIDENT', 'Resident'),
            ('STAFF', 'Security/Staff'),
            ('VISITOR', 'Visitor'),
        ],
        'total_users': users.count(),
    }
    return render(request, 'socity/admin/user_list.html', context)


@admin_required
def user_create(request):
    """Create a new user and assign role."""
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            user_obj = form.save()
            ensure_user_role_setup(user_obj)
            messages.success(request, 'User created successfully.')
            return redirect('user_list')
    else:
        form = AdminUserCreateForm()
    return render(request, 'socity/admin/user_form.html', {'form': form, 'title': 'Add User'})


@admin_required
def user_edit(request, user_id):
    """Edit user details and role assignment."""
    user_obj = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = AdminUserUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            user_obj = form.save()
            ensure_user_role_setup(user_obj)
            messages.success(request, 'User updated successfully.')
            return redirect('user_list')
    else:
        form = AdminUserUpdateForm(instance=user_obj)
    return render(request, 'socity/admin/user_form.html', {'form': form, 'title': 'Edit User', 'user_obj': user_obj})


@admin_required
def user_delete(request, user_id):
    """Delete user account."""
    user_obj = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user_obj.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('user_list')
    return render(request, 'socity/admin/user_confirm_delete.html', {'user_obj': user_obj})


@admin_required
def user_toggle_active(request, user_id):
    """Activate/deactivate user account."""
    user_obj = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user_obj.is_active = not user_obj.is_active
        user_obj.save(update_fields=['is_active'])
        messages.success(request, f"User {'activated' if user_obj.is_active else 'deactivated'} successfully.")
    return redirect('user_list')

@admin_required
def resident_list(request):
    """List all residents with search and filters"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    residents = Resident.objects.select_related('user', 'unit').all()
    
    if search_query:
        residents = residents.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(unit__unit_no__icontains=search_query)
        )
    
    if status_filter:
        residents = residents.filter(status=status_filter)
    
    context = {'residents': residents, 'search_query': search_query, 'status_choices': Resident.STATUS_CHOICES}
    return render(request, 'socity/admin/resident_list.html', context)


@admin_required
def resident_create(request):
    """Create resident account and assign to unit."""
    if request.method == 'POST':
        form = AdminResidentCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                email = form.cleaned_data['email']
                username = form.build_unique_username(email)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    role='RESIDENT',
                    phone=form.cleaned_data.get('phone') or '',
                    gender=form.cleaned_data.get('gender') or None,
                )
                unit = form.cleaned_data['unit']
                Resident.objects.create(
                    user=user,
                    unit=unit,
                    status=form.cleaned_data['status'],
                    vehicle_no=form.cleaned_data.get('vehicle_no') or '',
                    member_count=form.cleaned_data['member_count'],
                    move_in_date=form.cleaned_data['move_in_date'],
                    emergency_contact=form.cleaned_data.get('emergency_contact') or '',
                    emergency_phone=form.cleaned_data.get('emergency_phone') or '',
                    occupation=form.cleaned_data.get('occupation') or '',
                )
                if not unit.is_occupied:
                    unit.is_occupied = True
                    unit.save(update_fields=['is_occupied'])

            messages.success(request, 'Resident created successfully.')
            return redirect('resident_list')
    else:
        form = AdminResidentCreateForm()

    return render(request, 'socity/admin/resident_create.html', {'form': form})


@admin_required
def resident_detail(request, resident_id):
    """View detailed resident profile"""
    resident = get_object_or_404(Resident, id=resident_id)
    context = {
        'resident': resident,
        'bills': MaintenanceBill.objects.filter(unit=resident.unit),
        'complaints': Complaint.objects.filter(raised_by=resident),
        'bookings': AmenityBooking.objects.filter(resident=resident),
        'transactions': Transaction.objects.filter(resident=resident),
    }
    return render(request, 'socity/admin/resident_detail.html', context)


@admin_required
def resident_edit(request, resident_id):
    """Edit resident profile"""
    resident = get_object_or_404(Resident, id=resident_id)
    if request.method == 'POST':
        form = ResidentForm(request.POST, instance=resident)
        if form.is_valid():
            form.save()
            messages.success(request, 'Resident updated successfully.')
            return redirect('resident_detail', resident_id=resident_id)
    else:
        form = ResidentForm(instance=resident)
    return render(request, 'socity/admin/resident_form.html', {'form': form, 'resident': resident})


@admin_required
def resident_delete(request, resident_id):
    """Delete resident account"""
    resident = get_object_or_404(Resident, id=resident_id)
    if request.method == 'POST':
        user = resident.user
        resident.delete()
        user.delete()
        messages.success(request, 'Resident deleted successfully.')
        return redirect('resident_list')
    return render(request, 'socity/admin/resident_confirm_delete.html', {'resident': resident})


# ============= ADMIN: STAFF MANAGEMENT =============

@admin_required
def staff_list(request):
    """List all staff members"""
    search_query = request.GET.get('search', '')
    designation_filter = request.GET.get('designation', '')
    status_filter = request.GET.get('status', '')
    
    staff_members = Staff.objects.select_related('user').all()
    
    if search_query:
        staff_members = staff_members.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    if designation_filter:
        staff_members = staff_members.filter(designation=designation_filter)
    if status_filter:
        staff_members = staff_members.filter(status=status_filter)
    
    context = {'staff_members': staff_members, 'search_query': search_query, 
               'designation_choices': Staff.DESIGNATION_CHOICES, 'status_choices': Staff.STATUS_CHOICES}
    return render(request, 'socity/admin/staff_list.html', context)


@admin_required
def staff_create(request):
    """Create staff account and profile."""
    if request.method == 'POST':
        form = AdminStaffCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                email = form.cleaned_data['email']
                username = form.build_unique_username(email)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    role='STAFF',
                    phone=form.cleaned_data.get('phone') or '',
                    gender=form.cleaned_data.get('gender') or None,
                )

                Staff.objects.create(
                    user=user,
                    designation=form.cleaned_data['designation'],
                    department=form.cleaned_data.get('department') or '',
                    status=form.cleaned_data['status'],
                    join_date=form.cleaned_data['join_date'],
                    salary=form.cleaned_data.get('salary'),
                    emergency_contact=form.cleaned_data.get('emergency_contact') or '',
                    emergency_phone=form.cleaned_data.get('emergency_phone') or '',
                    address=form.cleaned_data.get('address') or '',
                )

            messages.success(request, 'Staff member created successfully.')
            return redirect('staff_list')
    else:
        form = AdminStaffCreateForm()

    return render(request, 'socity/admin/staff_create.html', {'form': form})


@admin_required
def staff_detail(request, staff_id):
    """View staff member details"""
    staff = get_object_or_404(Staff, id=staff_id)
    context = {
        'staff': staff,
        'assigned_tasks': Task.objects.filter(assigned_to=staff),
        'assigned_complaints': Complaint.objects.filter(assigned_to=staff.user),
    }
    return render(request, 'socity/admin/staff_detail.html', context)


@admin_required
def staff_edit(request, staff_id):
    """Edit staff profile"""
    staff = get_object_or_404(Staff, id=staff_id)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff updated successfully.')
            return redirect('staff_detail', staff_id=staff_id)
    else:
        form = StaffForm(instance=staff)
    return render(request, 'socity/admin/staff_form.html', {'form': form, 'staff': staff})


@admin_required
def staff_delete(request, staff_id):
    """Delete staff member"""
    staff = get_object_or_404(Staff, id=staff_id)
    if request.method == 'POST':
        user = staff.user
        staff.delete()
        user.delete()
        messages.success(request, 'Staff member deleted successfully.')
        return redirect('staff_list')
    return render(request, 'socity/admin/staff_confirm_delete.html', {'staff': staff})


# ============= ADMIN: UNIT/PROPERTY MANAGEMENT =============

@admin_required
def unit_list(request):
    """List all units/flats"""
    search_query = request.GET.get('search', '')
    occupied_filter = request.GET.get('occupied', '')
    
    units = Unit.objects.all()
    if search_query:
        units = units.filter(Q(unit_no__icontains=search_query) | Q(wing__icontains=search_query))
    if occupied_filter == 'yes':
        units = units.filter(is_occupied=True)
    elif occupied_filter == 'no':
        units = units.filter(is_occupied=False)
    
    context = {'units': units, 'search_query': search_query,
               'total_units': Unit.objects.count(), 'occupied_units': Unit.objects.filter(is_occupied=True).count()}
    return render(request, 'socity/admin/unit_list.html', context)


@admin_required
def unit_create(request):
    """Create new unit"""
    if request.method == 'POST':
        form = UnitForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unit created successfully.')
            return redirect('unit_list')
    else:
        form = UnitForm()
    return render(request, 'socity/admin/unit_form.html', {'form': form, 'title': 'Create Unit'})


@admin_required
def unit_edit(request, unit_id):
    """Edit unit"""
    unit = get_object_or_404(Unit, id=unit_id)
    if request.method == 'POST':
        form = UnitForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unit updated successfully.')
            return redirect('unit_list')
    else:
        form = UnitForm(instance=unit)
    return render(request, 'socity/admin/unit_form.html', {'form': form, 'unit': unit, 'title': 'Edit Unit'})


@admin_required
def unit_delete(request, unit_id):
    """Delete unit"""
    unit = get_object_or_404(Unit, id=unit_id)
    if request.method == 'POST':
        unit.delete()
        messages.success(request, 'Unit deleted successfully.')
        return redirect('unit_list')
    return render(request, 'socity/admin/unit_confirm_delete.html', {'unit': unit})


@admin_required
def building_list(request):
    """List all buildings"""
    buildings = Building.objects.all()
    return render(request, 'socity/admin/building_list.html', {'buildings': buildings})


@admin_required
def building_create(request):
    """Create new building"""
    if request.method == 'POST':
        form = BuildingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Building created successfully.')
            return redirect('building_list')
    else:
        form = BuildingForm()
    return render(request, 'socity/admin/building_form.html', {'form': form, 'title': 'Create Building'})


@admin_required
def building_edit(request, building_id):
    """Edit building"""
    building = get_object_or_404(Building, id=building_id)
    if request.method == 'POST':
        form = BuildingForm(request.POST, instance=building)
        if form.is_valid():
            form.save()
            messages.success(request, 'Building updated successfully.')
            return redirect('building_list')
    else:
        form = BuildingForm(instance=building)
    return render(request, 'socity/admin/building_form.html', {'form': form, 'building': building, 'title': 'Edit Building'})


# ============= ADMIN: BILLS & PAYMENTS =============

@admin_required
def bill_list(request):
    """List all maintenance bills"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    month_filter = request.GET.get('month', '')
    
    bills = MaintenanceBill.objects.select_related('unit').all()
    
    if search_query:
        bills = bills.filter(
            Q(unit__unit_no__icontains=search_query)
            | Q(unit__wing__icontains=search_query)
            | Q(unit__unit_type__icontains=search_query)
        )
    if status_filter:
        bills = bills.filter(status=status_filter)
    if month_filter:
        bills = bills.filter(billing_month__month=month_filter)

    paginator = Paginator(bills, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    context = {'bills': page_obj, 'page_obj': page_obj, 'search_query': search_query, 'status_choices': MaintenanceBill.PAYMENT_STATUS_CHOICES,
               'status_filter': status_filter, 'month_filter': month_filter,
               'total_pending_amount': bills.filter(status='PENDING').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')}
    return render(request, 'socity/admin/bill_list.html', context)


@admin_required
def bill_create(request):
    """Create new maintenance bill"""
    if request.method == 'POST':
        form = MaintenanceBillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.is_auto_generated = True
            if not bill.bill_date:
                bill.bill_date = bill.billing_month
            bill.save()

            residents = Resident.objects.filter(unit=bill.unit).select_related('user')
            for resident in residents:
                create_notification(
                    resident.user,
                    title='New Maintenance Bill Generated',
                    message=f'A bill for {bill.billing_month.strftime("%B %Y")} has been generated for your unit.',
                    notification_type='INFO',
                    action_url='/resident/bills/',
                    send_email=True,
                    email_subject='New Maintenance Bill Generated',
                )

            messages.success(request, 'Maintenance bill created successfully.')
            return redirect('bill_list')
    else:
        form = MaintenanceBillForm()
    return render(request, 'socity/admin/bill_form.html', {'form': form, 'title': 'Create Maintenance Bill'})


@admin_required
def bill_edit(request, bill_id):
    """Edit maintenance bill"""
    bill = get_object_or_404(MaintenanceBill, id=bill_id)
    if request.method == 'POST':
        form = MaintenanceBillForm(request.POST, instance=bill)
        if form.is_valid():
            form.save()
            messages.success(request, 'Maintenance bill updated successfully.')
            return redirect('bill_list')
    else:
        form = MaintenanceBillForm(instance=bill)
    return render(request, 'socity/admin/bill_form.html', {'form': form, 'bill': bill, 'title': 'Edit Maintenance Bill'})


@admin_required
def bill_delete(request, bill_id):
    """Delete maintenance bill"""
    bill = get_object_or_404(MaintenanceBill, id=bill_id)
    if request.method == 'POST':
        bill.delete()
        messages.success(request, 'Maintenance bill deleted successfully.')
        return redirect('bill_list')
    return render(request, 'socity/admin/bill_confirm_delete.html', {'bill': bill})


@admin_required
def bill_payment_history(request):
    """View payment history and reports"""
    transactions = Transaction.objects.select_related('resident', 'bill').order_by('-transaction_date')
    context = {'transactions': transactions,
               'total_collected': transactions.aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
               'total_pending': MaintenanceBill.objects.filter(status='PENDING').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')}
    return render(request, 'socity/admin/bill_payment_history.html', context)


# ============= ADMIN: COMPLAINT MANAGEMENT =============

@admin_required
def complaint_list(request):
    """List all complaints"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    
    complaints = Complaint.objects.select_related('raised_by', 'assigned_to').all()
    if search_query:
        complaints = complaints.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(raised_by__user__first_name__icontains=search_query)
            | Q(raised_by__user__last_name__icontains=search_query)
            | Q(raised_by__unit__unit_no__icontains=search_query)
        )
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    if category_filter:
        complaints = complaints.filter(category=category_filter)

    paginator = Paginator(complaints, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    context = {'complaints': page_obj, 'page_obj': page_obj, 'search_query': search_query,
               'status_filter': status_filter, 'category_filter': category_filter,
               'status_choices': Complaint.STATUS_CHOICES,
               'category_choices': Complaint.CATEGORY_CHOICES, 'total_complaints': Complaint.objects.count(),
               'open_complaints': Complaint.objects.filter(status='OPEN').count()}
    return render(request, 'socity/admin/complaint_list.html', context)


@admin_required
def complaint_detail(request, complaint_id):
    """View complaint details"""
    complaint = get_object_or_404(Complaint, id=complaint_id)
    updates = ComplaintUpdate.objects.filter(complaint=complaint).order_by('-update_date')
    context = {'complaint': complaint, 'updates': updates}
    return render(request, 'socity/admin/complaint_detail.html', context)


@admin_required
def complaint_update(request, complaint_id):
    """Admin update for complaint status, assignment, and comment log."""
    complaint = get_object_or_404(Complaint, id=complaint_id)

    if request.method == 'POST':
        form = AdminComplaintUpdateForm(request.POST)
        if form.is_valid():
            previous_status = complaint.status
            complaint.status = form.cleaned_data['status']
            complaint.assigned_to = form.cleaned_data['assigned_to']
            if complaint.status == 'RESOLVED' and not complaint.resolved_date:
                complaint.resolved_date = timezone.now()
            complaint.save()

            remarks = (form.cleaned_data.get('remarks') or '').strip()
            if remarks:
                ComplaintUpdate.objects.create(
                    complaint=complaint,
                    updated_by=request.user,
                    status=complaint.status,
                    remarks=remarks,
                )

            create_notification(
                complaint.raised_by.user,
                title='Complaint Updated',
                message=f'Your complaint "{complaint.title}" is now {complaint.get_status_display()}.',
                notification_type='INFO',
                action_url=f'/resident/complaints/{complaint.id}/',
                send_email=True,
                email_subject='Complaint Status Updated',
            )

            if complaint.assigned_to and complaint.assigned_to.role == 'STAFF':
                create_notification(
                    complaint.assigned_to,
                    title='Complaint Updated by Admin',
                    message=(
                        f'Complaint "{complaint.title}" changed from '
                        f'{previous_status.replace("_", " ").title()} to {complaint.get_status_display()}.'
                    ),
                    notification_type='INFO',
                    action_url='/staff/complaints/',
                    send_email=True,
                    email_subject='Complaint Updated by Admin',
                )

            messages.success(request, 'Complaint updated successfully.')
            return redirect('complaint_detail', complaint_id=complaint.id)
    else:
        form = AdminComplaintUpdateForm(initial={'status': complaint.status, 'assigned_to': complaint.assigned_to})

    return render(request, 'socity/admin/complaint_update.html', {'form': form, 'complaint': complaint})


@admin_required
def complaint_assign(request, complaint_id):
    """Assign complaint to staff"""
    complaint = get_object_or_404(Complaint, id=complaint_id)
    priority_map = {1: 'LOW', 2: 'MEDIUM', 3: 'HIGH'}

    if request.method == 'POST':
        staff_user_id = request.POST.get('assigned_to')
        if staff_user_id:
            staff_user = get_object_or_404(User, id=staff_user_id, role='STAFF')
            complaint.assigned_to = staff_user
            complaint.status = 'IN_PROGRESS'
            complaint.save()
            ComplaintUpdate.objects.create(
                complaint=complaint,
                updated_by=request.user,
                status='IN_PROGRESS',
                remarks=f'Complaint assigned to {staff_user.get_full_name() or staff_user.username}.',
            )
            
            # Create task for staff
            Task.objects.create(
                title=f"Resolve: {complaint.title}",
                description=complaint.description,
                assigned_to=staff_user.staff_profile,
                assigned_by=request.user,
                complaint=complaint,
                priority=priority_map.get(complaint.priority, 'MEDIUM'),
            )

            create_notification(
                staff_user,
                title='New Complaint Assigned',
                message=f'You were assigned complaint: {complaint.title}',
                notification_type='WARNING',
                action_url='/staff/complaints/',
                send_email=True,
                email_subject='New Complaint Assigned',
            )

            create_notification(
                complaint.raised_by.user,
                title='Complaint In Progress',
                message=f'Your complaint "{complaint.title}" has been assigned to staff.',
                notification_type='INFO',
                action_url=f'/resident/complaints/{complaint.id}/',
                send_email=True,
                email_subject='Complaint Assigned to Staff',
            )

            messages.success(request, 'Complaint assigned successfully.')
            return redirect('complaint_detail', complaint_id=complaint_id)
    
    staff_users = User.objects.filter(role='STAFF')
    return render(request, 'socity/admin/complaint_assign.html', {'complaint': complaint, 'staff_users': staff_users})


@admin_required
def complaint_close(request, complaint_id):
    """Close complaint"""
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.method == 'POST':
        complaint.status = 'RESOLVED'
        complaint.resolved_date = timezone.now()
        complaint.save()
        ComplaintUpdate.objects.create(
            complaint=complaint,
            updated_by=request.user,
            status='RESOLVED',
            remarks='Complaint marked as resolved by admin.',
        )

        create_notification(
            complaint.raised_by.user,
            title='Complaint Resolved',
            message=f'Your complaint "{complaint.title}" has been marked as resolved.',
            notification_type='SUCCESS',
            action_url=f'/resident/complaints/{complaint.id}/',
            send_email=True,
            email_subject='Complaint Resolved',
        )

        messages.success(request, 'Complaint closed successfully.')
        return redirect('complaint_detail', complaint_id=complaint_id)
    return render(request, 'socity/admin/complaint_confirm_close.html', {'complaint': complaint})


# ============= ADMIN: NOTICE MANAGEMENT =============

@admin_required
def notice_list(request):
    """List all notices"""
    notices = Notice.objects.all().order_by('-posted_date')
    context = {'notices': notices, 'total_notices': Notice.objects.count(),
               'active_notices': Notice.objects.filter(is_active=True).count()}
    return render(request, 'socity/admin/notice_list.html', context)


@admin_required
def notice_create(request):
    """Create new notice"""
    if request.method == 'POST':
        form = NoticeForm(request.POST, request.FILES)
        if form.is_valid():
            notice = form.save(commit=False)
            notice.posted_by = request.user
            notice.save()

            if form.cleaned_data.get('send_target') == 'SELECTED':
                recipients = list(form.cleaned_data['recipients'])
                NoticeRecipient.objects.bulk_create(
                    [NoticeRecipient(notice=notice, user=user) for user in recipients],
                    ignore_conflicts=True,
                )
            else:
                recipients = list(User.objects.filter(role__in=['ADMIN', 'RESIDENT', 'STAFF'], is_active=True))

            for target_user in recipients:
                create_notification(
                    target_user,
                    title=f'New Notice: {notice.title}',
                    message=notice.content[:220],
                    notification_type='INFO',
                    action_url='/dashboard/',
                    send_email=True,
                    email_subject='New Society Notice',
                )

            messages.success(request, 'Notice published successfully.')
            return redirect('notice_list')
    else:
        form = NoticeForm()
    return render(request, 'socity/admin/notice_form.html', {'form': form, 'title': 'Create Notice'})


@admin_required
def notice_edit(request, notice_id):
    """Edit notice"""
    notice = get_object_or_404(Notice, id=notice_id)
    if request.method == 'POST':
        form = NoticeForm(request.POST, request.FILES, instance=notice)
        if form.is_valid():
            form.save()

            notice.recipients.all().delete()
            if form.cleaned_data.get('send_target') == 'SELECTED':
                NoticeRecipient.objects.bulk_create(
                    [NoticeRecipient(notice=notice, user=user) for user in form.cleaned_data['recipients']],
                    ignore_conflicts=True,
                )

            messages.success(request, 'Notice updated successfully.')
            return redirect('notice_list')
    else:
        form = NoticeForm(instance=notice)
    return render(request, 'socity/admin/notice_form.html', {'form': form, 'notice': notice, 'title': 'Edit Notice'})


@admin_required
def notice_delete(request, notice_id):
    """Delete notice"""
    notice = get_object_or_404(Notice, id=notice_id)
    if request.method == 'POST':
        notice.delete()
        messages.success(request, 'Notice deleted successfully.')
        return redirect('notice_list')
    return render(request, 'socity/admin/notice_confirm_delete.html', {'notice': notice})


# Continue with Amenities, Visitor, and Resident/Staff views in next section
# (See IMPLEMENTATION_GUIDE.md for complete view listings)


# ============= ADMIN: AMENITIES MANAGEMENT =============

@admin_required
def amenity_list(request):
    """List all amenities"""
    amenities = Amenity.objects.all()
    context = {'amenities': amenities, 'total_amenities': Amenity.objects.count()}
    return render(request, 'socity/admin/amenity_list.html', context)


@admin_required
def amenity_create(request):
    """Create new amenity"""
    if request.method == 'POST':
        form = AmenityForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Amenity created successfully.')
            return redirect('amenity_list')
    else:
        form = AmenityForm()
    return render(request, 'socity/admin/amenity_form.html', {'form': form, 'title': 'Create Amenity'})


@admin_required
def amenity_edit(request, amenity_id):
    """Edit amenity"""
    amenity = get_object_or_404(Amenity, id=amenity_id)
    if request.method == 'POST':
        form = AmenityForm(request.POST, request.FILES, instance=amenity)
        if form.is_valid():
            form.save()
            messages.success(request, 'Amenity updated successfully.')
            return redirect('amenity_list')
    else:
        form = AmenityForm(instance=amenity)
    return render(request, 'socity/admin/amenity_form.html', {'form': form, 'amenity': amenity, 'title': 'Edit Amenity'})


@admin_required
def amenity_booking_list(request):
    """List amenity bookings for approval"""
    status_filter = request.GET.get('status', '')
    
    bookings = AmenityBooking.objects.select_related('resident', 'amenity').all()
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    context = {'bookings': bookings, 'status_choices': AmenityBooking.STATUS_CHOICES,
               'pending_bookings': AmenityBooking.objects.filter(status='PENDING').count()}
    return render(request, 'socity/admin/amenity_booking_list.html', context)


@admin_required
def amenity_booking_approve(request, booking_id):
    """Approve/Reject amenity booking"""
    booking = get_object_or_404(AmenityBooking, id=booking_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        booking.status = 'CONFIRMED' if action == 'approve' else 'CANCELLED'
        booking.save()
        messages.success(request, 'Booking approved successfully.' if action == 'approve' else 'Booking rejected.')
        return redirect('amenity_booking_list')
    return render(request, 'socity/admin/amenity_booking_approve.html', {'booking': booking})


@admin_required
def visitor_list(request):
    """List all visitors"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    approval_filter = request.GET.get('approval', '')
    
    visitors = Visitor.objects.select_related('visit_unit', 'host').all()
    if search_query:
        visitors = visitors.filter(
            Q(name__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(purpose__icontains=search_query)
            | Q(visit_unit__unit_no__icontains=search_query)
            | Q(visit_unit__wing__icontains=search_query)
        )
    if status_filter:
        visitors = visitors.filter(status=status_filter)
    if approval_filter:
        visitors = visitors.filter(approval_status=approval_filter)

    visitors = visitors.order_by('approval_status', '-in_time')
    
    context = {'visitors': visitors, 'search_query': search_query, 'status_choices': Visitor.STATUS_CHOICES,
               'approval_choices': Visitor.APPROVAL_STATUS_CHOICES, 'approval_filter': approval_filter,
               'today_visitors': Visitor.objects.filter(in_time__date=timezone.now().date()).count()}
    return render(request, 'socity/admin/visitor_list.html', context)


@admin_required
def visitor_approval_action(request, visitor_id):
    """Approve or reject a visitor log entry."""
    visitor = get_object_or_404(Visitor, id=visitor_id)
    if request.method == 'POST':
        form = VisitorApprovalActionForm(request.POST)
        if form.is_valid():
            visitor.approval_status = form.cleaned_data['action']
            visitor.approval_note = form.cleaned_data.get('approval_note', '')
            if visitor.approval_status == 'REJECTED' and visitor.status == 'IN':
                visitor.status = 'OUT'
                visitor.out_time = timezone.now()
            visitor.save(update_fields=['approval_status', 'approval_note', 'status', 'out_time'])

            action_word = 'approved' if visitor.approval_status == 'APPROVED' else 'rejected'
            for visitor_user in _get_visitor_notification_targets(visitor):
                create_notification(
                    visitor_user,
                    title=f'Visit Request {visitor.approval_status.title()}',
                    message=(
                        f'Your visit for {visitor.visit_unit} was {action_word}. '
                        f'{f"Note: {visitor.approval_note}" if visitor.approval_note else ""}'
                    ).strip(),
                    notification_type='SUCCESS' if visitor.approval_status == 'APPROVED' else 'WARNING',
                    action_url='/visitor/entry/?approval=' + visitor.approval_status,
                    send_email=True,
                    email_subject=f'Visit Request {visitor.approval_status.title()}',
                )

            messages.success(request, 'Visitor approval status updated.')
            return redirect('visitor_list')
    else:
        form = VisitorApprovalActionForm(initial={'action': visitor.approval_status, 'approval_note': visitor.approval_note})
    return render(request, 'socity/admin/visitor_approval_action.html', {'form': form, 'visitor': visitor})


@admin_required
def reports_dashboard(request):
    """Consolidated reporting for billing, occupancy, and complaints."""
    total_collection = Transaction.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    pending_amount = MaintenanceBill.objects.exclude(status='PAID').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    paid_amount = MaintenanceBill.objects.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or Decimal('0')

    complaints_by_status = {
        key: Complaint.objects.filter(status=key).count()
        for key, _ in Complaint.STATUS_CHOICES
    }

    context = {
        'total_collection': total_collection,
        'pending_amount': pending_amount,
        'paid_amount': paid_amount,
        'occupied_units': Unit.objects.filter(is_occupied=True).count(),
        'vacant_units': Unit.objects.filter(is_occupied=False).count(),
        'complaints_by_status': complaints_by_status,
        'today_visitors': Visitor.objects.filter(in_time__date=timezone.now().date()).count(),
        'recent_transactions': Transaction.objects.select_related('resident').order_by('-transaction_date')[:10],
    }
    return render(request, 'socity/admin/reports_dashboard.html', context)


@admin_required
def export_report_data(request):
    """Export core report datasets to CSV or Excel."""
    dataset = (request.GET.get('dataset') or 'complaints').strip().lower()
    export_format = (request.GET.get('format') or 'csv').strip().lower()

    dataset_config = {
        'users': {
            'headers': ['Username', 'Name', 'Email', 'Role', 'Active', 'Joined'],
            'rows': lambda: [
                [u.username, u.get_full_name(), u.email, u.get_role_display(), 'Yes' if u.is_active else 'No', u.date_joined.strftime('%Y-%m-%d %H:%M')]
                for u in User.objects.filter(role__in=['ADMIN', 'RESIDENT', 'STAFF']).order_by('-date_joined')
            ],
        },
        'complaints': {
            'headers': ['ID', 'Title', 'Category', 'Status', 'Raised By', 'Assigned To', 'Created At'],
            'rows': lambda: [
                [
                    c.id,
                    c.title,
                    c.get_category_display(),
                    c.get_status_display(),
                    c.raised_by.user.get_full_name(),
                    c.assigned_to.get_full_name() if c.assigned_to else '-',
                    c.created_at.strftime('%Y-%m-%d %H:%M'),
                ]
                for c in Complaint.objects.select_related('raised_by__user', 'assigned_to').order_by('-created_at')
            ],
        },
        'bills': {
            'headers': ['ID', 'Unit', 'Billing Month', 'Amount', 'Penalty', 'Status'],
            'rows': lambda: [
                [b.id, str(b.unit), b.billing_month.strftime('%Y-%m-%d'), str(b.amount), str(b.penalty), b.get_status_display()]
                for b in MaintenanceBill.objects.select_related('unit').order_by('-billing_month')
            ],
        },
        'payments': {
            'headers': ['ID', 'Resident', 'Amount', 'Type', 'Mode', 'Reference', 'Date'],
            'rows': lambda: [
                [
                    t.id,
                    t.resident.user.get_full_name(),
                    str(t.amount),
                    t.get_transaction_type_display(),
                    t.get_payment_mode_display(),
                    t.reference_no,
                    t.transaction_date.strftime('%Y-%m-%d %H:%M'),
                ]
                for t in Transaction.objects.select_related('resident__user').order_by('-transaction_date')
            ],
        },
        'visitors': {
            'headers': ['ID', 'Name', 'Phone', 'Unit', 'Approval', 'Status', 'In Time', 'Out Time'],
            'rows': lambda: [
                [
                    v.id,
                    v.name,
                    v.phone,
                    str(v.visit_unit),
                    v.get_approval_status_display(),
                    v.get_status_display(),
                    v.in_time.strftime('%Y-%m-%d %H:%M'),
                    v.out_time.strftime('%Y-%m-%d %H:%M') if v.out_time else '-',
                ]
                for v in Visitor.objects.select_related('visit_unit').order_by('-in_time')
            ],
        },
    }

    selected = dataset_config.get(dataset, dataset_config['complaints'])
    headers = selected['headers']
    rows = selected['rows']()

    if export_format == 'excel':
        try:
            from openpyxl import Workbook
        except ImportError:
            messages.error(request, 'openpyxl is required for Excel export. Falling back to CSV.')
            export_format = 'csv'
        else:
            wb = Workbook()
            ws = wb.active
            ws.title = dataset.title()
            ws.append(headers)
            for row in rows:
                ws.append(row)

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{dataset}_report.xlsx"'
            wb.save(response)
            return response

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{dataset}_report.csv"'
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(rows)
    return response


# ============= RESIDENT VIEWS =============

@resident_required
def resident_profile_view(request):
    """View resident profile"""
    try:
        resident = request.user.resident_profile
    except:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')
    return render(request, 'socity/resident/profile.html', {'resident': resident, 'user': request.user})


@resident_required
def resident_profile_edit(request):
    """Edit resident profile"""
    try:
        resident = request.user.resident_profile
    except:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')
    
    if request.method == 'POST':
        form = ResidentProfileForm(request.POST, instance=resident)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('resident_profile')
    else:
        form = ResidentProfileForm(instance=resident)
    return render(request, 'socity/resident/profile_edit.html', {'form': form})


@resident_required
def resident_bills_view(request):
    """View maintenance bills"""
    try:
        resident = request.user.resident_profile
    except:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')
    
    # Filter bills where the bill is for the resident's move_in_date or later
    # Use bill_date if set, otherwise use billing_month
    # Only show auto-generated bills to residents
    from django.db.models import F, Case, When, DateField
    bills = MaintenanceBill.objects.filter(
        unit=resident.unit,
        is_auto_generated=True,
    ).annotate(
        effective_date=Case(
            When(bill_date__isnull=False, then=F('bill_date')),
            default=F('billing_month'),
            output_field=DateField()
        )
    ).filter(
        effective_date__gte=resident.move_in_date
    ).order_by('-billing_month')
    
    context = {
        'bills': bills,
        'total_pending': bills.filter(status='PENDING').aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
        'total_paid': bills.filter(status='PAID').aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
        'resident': resident
    }
    return render(request, 'socity/resident/bills_list.html', context)


@resident_required
def resident_payment_view(request, bill_id):
    """Record payment for bill"""
    try:
        resident = request.user.resident_profile
    except:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')
    
    # Get the bill and verify that it belongs to the resident's unit
    bill = get_object_or_404(MaintenanceBill, id=bill_id, unit=resident.unit)
    
    # Verify bill is auto-generated (only system-generated bills can be paid by residents)
    if not bill.is_auto_generated:
        messages.error(request, 'You do not have access to this bill.')
        return redirect('socity:resident_bills')
    
    # Verify resident has access based on move_in_date
    effective_date = bill.bill_date if bill.bill_date else bill.billing_month
    if effective_date < resident.move_in_date:
        messages.error(request, 'You do not have access to this bill.')
        return redirect('socity:resident_bills')
    
    if bill.status == 'PAID':
        messages.info(request, 'This bill has already been paid.')
        return redirect('socity:resident_bills')
    
    if request.method == 'POST':
        if request.POST.get('quick_pay') == '1':
            reference_no = f"MANUAL-{uuid.uuid4().hex[:10].upper()}"
            while Transaction.objects.filter(reference_no=reference_no).exists():
                reference_no = f"MANUAL-{uuid.uuid4().hex[:10].upper()}"

            Transaction.objects.create(
                bill=bill,
                resident=resident,
                amount=bill.amount + (bill.penalty or Decimal('0')),
                transaction_type='MAINTENANCE',
                payment_mode='UPI',
                reference_no=reference_no,
                remarks='Quick manual payment recorded by resident',
            )

            bill.status = 'PAID'
            bill.payment_mode = 'UPI'
            bill.payment_date = timezone.now()
            bill.save(update_fields=['status', 'payment_mode', 'payment_date'])

            messages.success(request, 'Bill paid successfully!')
            return redirect('resident_bills')

        form = PaymentForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.bill = bill
            transaction.resident = resident
            transaction.transaction_type = 'MAINTENANCE'
            transaction.save()
            
            bill.status = 'PAID'
            bill.payment_date = timezone.now()
            bill.save()
            
            messages.success(request, 'Payment recorded successfully!')
            return redirect('resident_bills')
    else:
        form = PaymentForm(initial={'amount': bill.amount + (bill.penalty or Decimal('0')), 'payment_mode': 'UPI'})
    
    return render(
        request,
        'socity/resident/bills_pay.html',
        {'form': form, 'bill': bill, 'stripe_configured': bool(settings.STRIPE_SECRET_KEY)},
    )


@resident_required
def resident_upi_qr_checkout(request, bill_id):
    """Simulated UPI/QR checkout for maintenance bill payment."""
    try:
        resident = request.user.resident_profile
    except Exception:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')

    bill = get_object_or_404(MaintenanceBill, id=bill_id, unit=resident.unit)
    
    # Verify bill is auto-generated (only system-generated bills can be paid by residents)
    if not bill.is_auto_generated:
        messages.error(request, 'You do not have access to this bill.')
        return redirect('socity:resident_bills')
    
    # Verify resident has access based on move_in_date
    effective_date = bill.bill_date if bill.bill_date else bill.billing_month
    if effective_date < resident.move_in_date:
        messages.error(request, 'You do not have access to this bill.')
        return redirect('socity:resident_bills')

    if bill.status == 'PAID':
        messages.info(request, 'This bill has already been paid.')
        return redirect('socity:resident_bills')

    payable_amount = bill.amount + (bill.penalty or Decimal('0'))
    payee_upi_id = getattr(settings, 'UPI_COLLECTOR_ID', 'gohilvijay53949@oksbi')
    payee_name = getattr(settings, 'UPI_COLLECTOR_NAME', 'Vijay gohil')
    txn_note = f"Maintenance {bill.billing_month.strftime('%b %Y')} - Bill #{bill.id}"

    upi_params = {
        'pa': payee_upi_id,
        'pn': payee_name,
        'am': f"{payable_amount:.2f}",
        'cu': 'INR',
        'tn': txn_note,
        'tr': f"BILL{bill.id}",
    }
    upi_deep_link = f"upi://pay?{urlencode(upi_params)}"
    qr_image_url = f"https://quickchart.io/qr?size=280&text={upi_deep_link}"

    if request.method == 'POST':
        utr_no = (request.POST.get('utr_no') or '').strip().upper()
        if len(utr_no) < 6:
            messages.error(request, 'Please enter a valid UPI/UTR reference number.')
            return redirect('socity:resident_upi_qr_checkout', bill_id=bill.id)

        reference_no = f"UPI-{utr_no}"
        if Transaction.objects.filter(reference_no=reference_no).exists():
            messages.error(request, 'This UPI reference is already used. Please check and try again.')
            return redirect('socity:resident_upi_qr_checkout', bill_id=bill.id)

        Transaction.objects.create(
            bill=bill,
            resident=resident,
            amount=payable_amount,
            transaction_type='MAINTENANCE',
            payment_mode='UPI',
            reference_no=reference_no,
            remarks='UPI/QR payment recorded by resident',
        )

        bill.status = 'PAID'
        bill.payment_mode = 'UPI'
        bill.payment_date = timezone.now()
        bill.save(update_fields=['status', 'payment_mode', 'payment_date'])

        messages.success(request, 'UPI/QR payment recorded successfully!')
        return redirect('socity:resident_bills')

    return render(
        request,
        'socity/resident/bills_pay_upi_qr.html',
        {
            'bill': bill,
            'payable_amount': payable_amount,
            'payee_upi_id': payee_upi_id,
            'payee_name': payee_name,
            'upi_deep_link': upi_deep_link,
            'qr_image_url': qr_image_url,
            'txn_note': txn_note,
        },
    )


@resident_required
def resident_stripe_checkout(request, bill_id):
    """Create Stripe checkout session for a maintenance bill."""
    try:
        resident = request.user.resident_profile
    except Exception:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')

    bill = get_object_or_404(MaintenanceBill, id=bill_id, unit=resident.unit)
    
    # Verify bill is auto-generated (only system-generated bills can be paid by residents)
    if not bill.is_auto_generated:
        messages.error(request, 'You do not have access to this bill.')
        return redirect('socity:resident_bills')
    
    # Verify resident has access based on move_in_date
    effective_date = bill.bill_date if bill.bill_date else bill.billing_month
    if effective_date < resident.move_in_date:
        messages.error(request, 'You do not have access to this bill.')
        return redirect('socity:resident_bills')
    
    if bill.status == 'PAID':
        messages.info(request, 'This bill has already been paid.')
        return redirect('resident_bills')

    if request.method != 'POST':
        return redirect('resident_payment', bill_id=bill.id)

    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, 'Stripe is not configured yet. Please use manual payment.')
        return redirect('resident_payment', bill_id=bill.id)

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        amount_paise = int((bill.amount + bill.penalty) * 100)
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='payment',
            line_items=[
                {
                    'price_data': {
                        'currency': 'inr',
                        'product_data': {
                            'name': f'Maintenance Bill - {bill.unit}',
                            'description': f'Billing month: {bill.billing_month.strftime("%B %Y")}',
                        },
                        'unit_amount': amount_paise,
                    },
                    'quantity': 1,
                }
            ],
            metadata={
                'bill_id': str(bill.id),
                'resident_id': str(resident.id),
            },
            success_url=f"{settings.APP_BASE_URL}/resident/bills/{bill.id}/stripe/success/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.APP_BASE_URL}/resident/bills/{bill.id}/pay/",
        )
        return redirect(checkout_session.url)
    except Exception:
        messages.error(request, 'Unable to initiate online payment right now. Please try again.')
        return redirect('resident_payment', bill_id=bill.id)


@resident_required
def resident_demo_online_checkout(request, bill_id):
    """Simulated online checkout flow for demo/testing environments."""
    try:
        resident = request.user.resident_profile
    except Exception:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')

    bill = get_object_or_404(MaintenanceBill, id=bill_id, unit=resident.unit)
    
    # Verify bill is auto-generated (only system-generated bills can be paid by residents)
    if not bill.is_auto_generated:
        messages.error(request, 'You do not have access to this bill.')
        return redirect('socity:resident_bills')
    
    # Verify resident has access based on move_in_date
    effective_date = bill.bill_date if bill.bill_date else bill.billing_month
    if effective_date < resident.move_in_date:
        messages.error(request, 'You do not have access to this bill.')
        return redirect('socity:resident_bills')
    
    if bill.status == 'PAID':
        messages.info(request, 'This bill has already been paid.')
        return redirect('socity:resident_bills')

    session_key = f"demo_payment_{request.user.id}_{bill.id}"
    pending = request.session.get(session_key)

    def _mask_email(email):
        if not email or '@' not in email:
            return email
        local, domain = email.split('@', 1)
        if len(local) > 2:
            local = local[:2] + ('*' * max(len(local) - 2, 1))
        else:
            local = local[:1] + '*'
        return f'{local}@{domain}'

    def _send_payment_otp(recipient_email, otp_value):
        send_mail(
            subject='e-Socity Payment OTP',
            message=(
                f'Hello {request.user.get_full_name() or request.user.username},\n\n'
                f'Your OTP for maintenance bill payment is: {otp_value}\n\n'
                'This OTP is for demo payment verification and should not be shared.'
            ),
            from_email=getattr(settings, 'EMAIL_HOST_USER', ''),
            recipient_list=[recipient_email],
            fail_silently=False,
        )

    if request.method == 'POST':
        stage = request.POST.get('stage') or 'card'

        if stage == 'card':
            card_name = (request.POST.get('card_name') or '').strip()
            card_number = ''.join(ch for ch in (request.POST.get('card_number') or '') if ch.isdigit())
            expiry = (request.POST.get('expiry') or '').strip()
            cvv = ''.join(ch for ch in (request.POST.get('cvv') or '') if ch.isdigit())

            if not card_name:
                messages.error(request, 'Card holder name is required.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)
            if len(card_number) != 16:
                messages.error(request, 'Enter a valid 16-digit card number.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)
            if len(cvv) not in [3, 4]:
                messages.error(request, 'Enter a valid CVV.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)
            if '/' not in expiry or len(expiry) != 5:
                messages.error(request, 'Enter expiry in MM/YY format.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)

            otp = str(random.randint(100000, 999999))
            recipient_email = (request.user.email or '').strip()
            if not recipient_email:
                messages.error(request, 'Email address not found. Please update your profile email to receive OTP.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)

            request.session[session_key] = {
                'card_name': card_name,
                'card_last4': card_number[-4:],
                'expiry': expiry,
                'otp': otp,
                'email': recipient_email,
                'created_at': timezone.now().isoformat(),
                'sent_at': timezone.now().isoformat(),
            }
            request.session.modified = True

            try:
                _send_payment_otp(recipient_email, otp)
            except Exception:
                request.session.pop(session_key, None)
                messages.error(request, 'Unable to send OTP email right now. Please try again in a moment.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)

            messages.info(request, f'OTP has been sent to your email: {_mask_email(recipient_email)}')
            return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)

        if stage == 'resend_otp':
            pending = request.session.get(session_key)
            if not pending:
                messages.error(request, 'Payment session expired. Please enter card details again.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)

            recipient_email = (pending.get('email') or '').strip()
            if not recipient_email:
                request.session.pop(session_key, None)
                messages.error(request, 'Email details missing. Please restart payment.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)

            sent_at_str = pending.get('sent_at') or ''
            can_resend = True
            if sent_at_str:
                try:
                    sent_at = datetime.fromisoformat(sent_at_str)
                    can_resend = timezone.now() >= (sent_at + timedelta(seconds=30))
                except ValueError:
                    can_resend = True

            if not can_resend:
                messages.warning(request, 'Please wait 30 seconds before requesting another OTP.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)

            otp = str(random.randint(100000, 999999))
            pending['otp'] = otp
            pending['sent_at'] = timezone.now().isoformat()
            request.session[session_key] = pending
            request.session.modified = True

            try:
                _send_payment_otp(recipient_email, otp)
            except Exception:
                messages.error(request, 'Unable to resend OTP email right now. Please try again in a moment.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)

            messages.success(request, f'New OTP sent to {_mask_email(recipient_email)}')
            return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)

        if stage == 'otp':
            otp_value = (request.POST.get('otp') or '').strip()
            pending = request.session.get(session_key)
            if not pending:
                messages.error(request, 'Payment session expired. Please enter card details again.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)
            if otp_value != pending.get('otp'):
                messages.error(request, 'Invalid OTP. Please try again.')
                return redirect('socity:resident_demo_online_checkout', bill_id=bill.id)

            reference_no = f"DEMO-{uuid.uuid4().hex[:12].upper()}"
            while Transaction.objects.filter(reference_no=reference_no).exists():
                reference_no = f"DEMO-{uuid.uuid4().hex[:12].upper()}"

            Transaction.objects.create(
                bill=bill,
                resident=resident,
                amount=bill.amount + (bill.penalty or Decimal('0')),
                transaction_type='MAINTENANCE',
                payment_mode='ONLINE',
                reference_no=reference_no,
                remarks=(
                    'Demo online payment (simulated gateway) '
                    f'| Card ****{pending.get("card_last4", "0000")}'
                ),
            )

            bill.status = 'PAID'
            bill.payment_mode = 'ONLINE'
            bill.payment_date = timezone.now()
            bill.save(update_fields=['status', 'payment_mode', 'payment_date'])

            request.session.pop(session_key, None)
            messages.success(request, f'Demo online payment successful. Ref: {reference_no}')
            return redirect('socity:resident_bills')

    return render(
        request,
        'socity/resident/bills_pay_demo.html',
        {
            'bill': bill,
            'payable_amount': bill.amount + (bill.penalty or Decimal('0')),
            'pending_payment': pending,
        },
    )


@resident_required
def resident_stripe_success(request, bill_id):
    """Finalize Stripe payment and mark maintenance bill as paid."""
    try:
        resident = request.user.resident_profile
    except Exception:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')

    bill = get_object_or_404(MaintenanceBill, id=bill_id, unit=resident.unit)
    
    # Verify bill is auto-generated (only system-generated bills can be paid by residents)
    if not bill.is_auto_generated:
        messages.error(request, 'You do not have access to this bill.')
        return redirect('socity:resident_bills')
    
    # Verify resident has access based on move_in_date
    effective_date = bill.bill_date if bill.bill_date else bill.billing_month
    if effective_date < resident.move_in_date:
        messages.error(request, 'You do not have access to this bill.')
        return redirect('socity:resident_bills')
    session_id = request.GET.get('session_id')
    if not session_id or not settings.STRIPE_SECRET_KEY:
        messages.error(request, 'Invalid payment verification request.')
        return redirect('resident_payment', bill_id=bill.id)

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        messages.error(request, 'Unable to verify payment at the moment.')
        return redirect('resident_payment', bill_id=bill.id)

    if session.get('payment_status') != 'paid':
        messages.error(request, 'Payment was not completed.')
        return redirect('resident_payment', bill_id=bill.id)

    reference_no = f"STRIPE-{session_id[-18:]}"
    if not Transaction.objects.filter(reference_no=reference_no).exists():
        Transaction.objects.create(
            bill=bill,
            resident=resident,
            amount=bill.amount + bill.penalty,
            transaction_type='MAINTENANCE',
            payment_mode='ONLINE',
            reference_no=reference_no,
            remarks='Stripe online payment',
        )

    bill.status = 'PAID'
    bill.payment_mode = 'ONLINE'
    bill.payment_date = timezone.now()
    bill.save(update_fields=['status', 'payment_mode', 'payment_date'])

    messages.success(request, 'Online payment successful and bill marked as paid.')
    return redirect('resident_bills')


@resident_required
def resident_bill_pdf_download(request, bill_id):
    """Generate and download maintenance bill as PDF for resident."""
    try:
        resident = request.user.resident_profile
    except Exception:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')

    billing_start = resident.move_in_date
    bill = get_object_or_404(
        MaintenanceBill,
        id=bill_id,
        unit=resident.unit,
        billing_month__gte=billing_start,
    )

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
    except ImportError:
        messages.error(request, 'PDF library is not available. Please install reportlab.')
        return redirect('resident_bills')

    pdf_context = {
        'resident': resident,
        'bill': bill,
        'generated_at': timezone.now(),
    }
    bill_text = render_to_string('socity/resident/bill_pdf.txt', pdf_context)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    text = pdf.beginText(40, height - 50)
    text.setFont('Helvetica', 10)

    # Render template output line-by-line in PDF.
    for line in bill_text.splitlines():
        text.textLine(line)

    pdf.drawText(text)
    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="maintenance_bill_{bill.id}.pdf"'
    return response


@resident_required
def resident_complaint_list(request):
    """View resident complaints"""
    try:
        resident = request.user.resident_profile
    except:
        return redirect('home')
    
    complaints = Complaint.objects.filter(raised_by=resident).order_by('-created_at')
    return render(request, 'socity/resident/complaints_list.html', {'complaints': complaints})


@resident_required
def resident_complaint_create(request):
    """File new complaint"""
    try:
        resident = request.user.resident_profile
    except:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')
    
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.raised_by = resident

            # Assign to the least-loaded active staff user so new complaints are actionable.
            staff_user = (
                User.objects.filter(
                    role='STAFF',
                    is_active=True,
                    staff_profile__status='ACTIVE',
                )
                .annotate(
                    open_assigned_count=Count(
                        'assigned_complaints',
                        filter=Q(assigned_complaints__status__in=['OPEN', 'IN_PROGRESS'])
                    )
                )
                .order_by('open_assigned_count', 'id')
                .first()
            )

            if not staff_user:
                staff_user = (
                    User.objects.filter(role='STAFF', is_active=True)
                    .annotate(
                        open_assigned_count=Count(
                            'assigned_complaints',
                            filter=Q(assigned_complaints__status__in=['OPEN', 'IN_PROGRESS'])
                        )
                    )
                    .order_by('open_assigned_count', 'id')
                    .first()
                )

            complaint.assigned_to = staff_user
            complaint.save()

            # Notify all admins of new complaint
            admin_users = User.objects.filter(role='ADMIN', is_active=True)
            for admin_user in admin_users:
                create_notification(
                    admin_user,
                    title='New Complaint Filed',
                    message=(
                        f'New complaint "{complaint.title}" from {resident.user.get_full_name() or resident.user.username} '
                        f'({resident.unit}). Category: {complaint.get_category_display()}'
                    ),
                    notification_type='INFO',
                    action_url='/management/complaints/',
                    send_email=True,
                    email_subject='New Complaint Filed',
                )

            if staff_user:
                create_notification(
                    staff_user,
                    title='New Complaint Assigned',
                    message=(
                        f'Complaint "{complaint.title}" has been assigned to you '
                        f'from unit {resident.unit}.'
                    ),
                    notification_type='INFO',
                    action_url='/staff/complaints/',
                    send_email=True,
                    email_subject='New Complaint Assigned',
                )
                messages.success(
                    request,
                    f'Complaint filed successfully and assigned to staff: '
                    f'{staff_user.get_full_name() or staff_user.username}.',
                )
            else:
                messages.success(request, 'Complaint filed successfully!')
                messages.warning(request, 'No active staff found. Admin will assign this complaint manually.')

            return redirect('resident_complaints')
    else:
        form = ComplaintForm()
    
    return render(request, 'socity/resident/complaints_create.html', {'form': form})


@resident_required
def resident_complaint_detail(request, complaint_id):
    """View complaint details"""
    try:
        resident = request.user.resident_profile
    except:
        return redirect('home')
    
    complaint = get_object_or_404(Complaint, id=complaint_id, raised_by=resident)
    updates = ComplaintUpdate.objects.filter(complaint=complaint).order_by('-update_date')
    context = {'complaint': complaint, 'updates': updates}
    return render(request, 'socity/resident/complaints_detail.html', context)


@resident_required
def resident_amenities_view(request):
    """View available amenities"""
    amenities = Amenity.objects.filter(is_available=True)
    return render(request, 'socity/resident/amenities_list.html', {'amenities': amenities})


@resident_required
def resident_amenity_book(request, amenity_id=None):
    """Book an amenity"""
    try:
        resident = request.user.resident_profile
    except:
        messages.error(request, 'Resident profile not found.')
        return redirect('resident_amenities')
    
    if request.method == 'POST':
        form = AmenityBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.resident = resident
            booking.save()

            admin_users = User.objects.filter(role='ADMIN', is_active=True)
            for admin_user in admin_users:
                create_notification(
                    admin_user,
                    title='New Amenity Booking Request',
                    message=(
                        f"{resident.user.get_full_name() or resident.user.username} requested "
                        f"{booking.amenity.name} for {booking.booking_date}."
                    ),
                    notification_type='INFO',
                    action_url='/management/amenities/bookings/',
                    send_email=True,
                    email_subject='New Amenity Booking Request',
                )

            messages.success(request, 'Amenity booked! Awaiting approval.')
            return redirect('resident_bookings')
    else:
        form = AmenityBookingForm()
    
    return render(request, 'socity/resident/amenities_book.html', {'form': form})


@resident_required
def resident_booking_list(request):
    """View amenity bookings"""
    try:
        resident = request.user.resident_profile
    except:
        return redirect('home')
    
    bookings = AmenityBooking.objects.filter(resident=resident).order_by('-booking_date')
    return render(request, 'socity/resident/bookings_list.html', {'bookings': bookings})


@resident_required
def resident_booking_cancel(request, booking_id):
    """Allow residents to cancel pending/confirmed bookings."""
    resident = request.user.resident_profile
    booking = get_object_or_404(AmenityBooking, id=booking_id, resident=resident)

    if request.method == 'POST':
        if booking.status in ['PENDING', 'CONFIRMED']:
            booking.status = 'CANCELLED'
            booking.save(update_fields=['status'])

            admin_users = User.objects.filter(role='ADMIN', is_active=True)
            for admin_user in admin_users:
                create_notification(
                    admin_user,
                    title='Amenity Booking Cancelled',
                    message=(
                        f"{resident.user.get_full_name() or resident.user.username} cancelled "
                        f"{booking.amenity.name} booking on {booking.booking_date}."
                    ),
                    notification_type='WARNING',
                    action_url='/management/amenities/bookings/',
                )

            messages.success(request, 'Booking cancelled successfully.')
        else:
            messages.warning(request, 'This booking cannot be cancelled now.')
        return redirect('resident_bookings')

    return render(request, 'socity/resident/bookings_cancel.html', {'booking': booking})


@resident_required
def resident_notice_list(request):
    """View society notices"""
    notices = [
        notice for notice in Notice.objects.filter(is_active=True).order_by('-posted_date')
        if notice.is_visible_to(request.user)
    ]
    return render(request, 'socity/resident/notices_list.html', {'notices': notices})


@resident_required
def resident_notice_detail(request, notice_id):
    """View notice details"""
    notice = get_object_or_404(Notice, id=notice_id, is_active=True)
    return render(request, 'socity/resident/notices_detail.html', {'notice': notice})


@resident_required
def resident_transactions(request):
    """Resident payment transaction history."""
    resident = request.user.resident_profile
    transactions = Transaction.objects.filter(resident=resident).order_by('-transaction_date')
    total_amount = transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    return render(
        request,
        'socity/resident/transactions_list.html',
        {'transactions': transactions, 'total_amount': total_amount},
    )


@resident_required
def resident_visitor_approval(request):
    """Manage visitor pre-approvals"""
    try:
        resident = request.user.resident_profile
    except:
        return redirect('home')
    
    if request.method == 'POST':
        form = VisitorApprovalForm(request.POST)
        if form.is_valid():
            approval = form.save(commit=False)
            approval.resident = resident
            approval.save()
            messages.success(request, 'Visitor pre-approved!')
            return redirect('resident_visitor_approvals')
    else:
        form = VisitorApprovalForm()
    
    approvals = VisitorApproval.objects.filter(resident=resident).order_by('-created_at')
    context = {'form': form, 'approvals': approvals}
    return render(request, 'socity/resident/visitor_approvals.html', context)


@resident_required
def resident_visitor_list(request):
    """View visitor history"""
    try:
        resident = request.user.resident_profile
    except:
        return redirect('home')
    
    visitors = Visitor.objects.filter(visit_unit=resident.unit).only(
        'name', 'phone', 'email', 'purpose', 'vehicle_no', 'status', 'in_time', 'out_time', 'visit_unit'
    ).order_by('-in_time')
    return render(request, 'socity/resident/visitor_log.html', {'visitors': visitors})


# ============= STAFF VIEWS =============

@staff_required
def staff_task_list(request):
    """View assigned tasks"""
    try:
        staff = request.user.staff_profile
    except:
        return redirect('home')
    
    status_filter = request.GET.get('status', '')
    tasks = Task.objects.filter(assigned_to=staff)
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    context = {'tasks': tasks, 'status_choices': Task.STATUS_CHOICES}
    return render(request, 'socity/staff/tasks_list.html', context)


@staff_required
def staff_task_update(request, task_id):
    """Update task status"""
    try:
        staff = request.user.staff_profile
    except:
        return redirect('home')
    
    task = get_object_or_404(Task, id=task_id, assigned_to=staff)
    if request.method == 'POST':
        form = TaskUpdateForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully.')
            return redirect('staff_tasks')
    else:
        form = TaskUpdateForm(instance=task)
    
    return render(request, 'socity/staff/tasks_update.html', {'form': form, 'task': task})


@staff_required
def staff_complaint_list(request):
    """View assigned complaints"""
    staff = request.user.staff_profile
    complaints = _get_staff_accessible_complaints(request.user, staff).order_by('-created_at')
    available_complaints = Complaint.objects.filter(
        assigned_to__isnull=True,
        status='OPEN',
    ).select_related('raised_by__user').order_by('-created_at')

    return render(
        request,
        'socity/staff/complaints_list.html',
        {
            'complaints': complaints,
            'available_complaints': available_complaints,
            'assigned_count': complaints.count(),
            'available_count': available_complaints.count(),
        },
    )


@staff_required
@require_http_methods(["POST"])
def staff_claim_complaint(request, complaint_id):
    """Allow staff to claim an open unassigned complaint."""
    staff = request.user.staff_profile
    complaint = get_object_or_404(Complaint, id=complaint_id)

    if complaint.assigned_to_id and complaint.assigned_to_id != request.user.id:
        messages.error(request, 'This complaint is already assigned to another staff member.')
        return redirect('staff_complaints')

    if complaint.status == 'CLOSED':
        messages.error(request, 'Closed complaints cannot be claimed.')
        return redirect('staff_complaints')

    if complaint.assigned_to_id != request.user.id:
        complaint.assigned_to = request.user
        complaint.status = 'IN_PROGRESS'
        complaint.save(update_fields=['assigned_to', 'status'])

        ComplaintUpdate.objects.create(
            complaint=complaint,
            updated_by=request.user,
            status='IN_PROGRESS',
            remarks=(
                f'Complaint claimed by {request.user.get_full_name() or request.user.username}.'
            ),
        )

        Task.objects.get_or_create(
            complaint=complaint,
            assigned_to=staff,
            defaults={
                'title': f'Resolve: {complaint.title}',
                'description': complaint.description,
                'assigned_by': request.user,
                'priority': {1: 'LOW', 2: 'MEDIUM', 3: 'HIGH'}.get(complaint.priority, 'MEDIUM'),
                'status': 'PENDING',
            },
        )

        staff_name = request.user.get_full_name() or request.user.username
        for admin_user in User.objects.filter(role='ADMIN', is_active=True):
            create_notification(
                admin_user,
                title='Complaint Claimed by Staff',
                message=f'{staff_name} claimed complaint "{complaint.title}".',
                notification_type='INFO',
                action_url=f'/management/complaints/{complaint.id}/',
                send_email=True,
                email_subject='Complaint Claimed by Staff',
            )

        messages.success(request, 'Complaint claimed successfully.')
    else:
        messages.info(request, 'This complaint is already assigned to you.')

    return redirect('staff_complaints')


@staff_required
def staff_complaint_status_update(request, complaint_id):
    """Update complaint status"""
    staff = request.user.staff_profile
    complaint = get_object_or_404(_get_staff_accessible_complaints(request.user, staff), id=complaint_id)
    
    if request.method == 'POST':
        form = ComplaintUpdateForm(request.POST)
        if form.is_valid():
            previous_status = complaint.status
            update = form.save(commit=False)
            update.complaint = complaint
            update.updated_by = request.user
            update.save()
            
            complaint.status = form.cleaned_data['status']
            complaint.save()

            status_label = complaint.get_status_display()
            updater_name = request.user.get_full_name() or request.user.username
            action_url = f'/management/complaints/{complaint.id}/'

            for admin_user in User.objects.filter(role='ADMIN', is_active=True):
                create_notification(
                    admin_user,
                    title='Complaint Status Updated by Staff',
                    message=(
                        f'Complaint "{complaint.title}" changed from '
                        f'{previous_status.replace("_", " ").title()} to {status_label} by {updater_name}.'
                    ),
                    notification_type='INFO',
                    action_url=action_url,
                    send_email=True,
                    email_subject='Complaint Status Updated',
                )
            
            messages.success(request, 'Complaint status updated!')
            return redirect('staff_complaints')
    else:
        form = ComplaintUpdateForm()
    
    return render(request, 'socity/staff/complaints_status.html', {'form': form, 'complaint': complaint})


@staff_required
def staff_visitor_list(request):
    """View visitor list"""
    date_filter = request.GET.get('date', '')
    status_filter = request.GET.get('status', '')
    search_query = (request.GET.get('search') or '').strip()
    approval_filter = request.GET.get('approval', '')
    
    visitors = Visitor.objects.select_related('visit_unit').all()
    if search_query:
        visitors = visitors.filter(
            Q(name__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(purpose__icontains=search_query)
            | Q(visit_unit__unit_no__icontains=search_query)
            | Q(visit_unit__wing__icontains=search_query)
        )
    if date_filter:
        visitors = visitors.filter(in_time__date=date_filter)
    if status_filter:
        visitors = visitors.filter(status=status_filter)
    if approval_filter:
        visitors = visitors.filter(approval_status=approval_filter)

    visitors = visitors.order_by('-in_time')
    
    return render(request, 'socity/staff/visitors_list.html', {
        'visitors': visitors,
        'status_choices': Visitor.STATUS_CHOICES,
        'approval_choices': Visitor.APPROVAL_STATUS_CHOICES,
        'search_query': search_query,
        'date_filter': date_filter,
        'status_filter': status_filter,
        'approval_filter': approval_filter,
    })


@staff_required
def staff_visitor_entry(request):
    """Register visitor entry"""
    if request.method == 'POST':
        form = VisitorRegistrationForm(request.POST)
        if form.is_valid():
            visitor = form.save(commit=False)
            unit_no = form.cleaned_data.get('unit_no')
            resolved_unit = _resolve_unit_from_input(unit_no)
            if resolved_unit:
                visitor.visit_unit = resolved_unit
                visitor.host = _get_active_host_for_unit(resolved_unit)
                visitor.save()

                for admin_user in User.objects.filter(role='ADMIN', is_active=True):
                    create_notification(
                        admin_user,
                        title='New Visitor Entry Registered by Staff',
                        message=(
                            f'Staff registered visitor {visitor.name}'
                            f'{f" ({visitor.email})" if visitor.email else ""} for {visitor.visit_unit} '
                            f'({visitor.purpose}).'
                        ),
                        notification_type='INFO',
                        action_url='/management/visitors/',
                        send_email=True,
                        email_subject='New Visitor Entry Registered',
                    )

                messages.success(request, 'Visitor entry registered!')
                return redirect('staff_visitors')
            else:
                messages.error(request, 'Unit not found.')
    else:
        form = VisitorRegistrationForm()
    
    return render(request, 'socity/staff/visitors_entry.html', {'form': form})


@staff_required
def staff_visitor_exit(request, visitor_id):
    """Record visitor exit"""
    visitor = get_object_or_404(Visitor, id=visitor_id)
    
    if request.method == 'POST':
        if visitor.status == 'OUT':
            messages.info(request, 'Visitor exit is already recorded.')
            return redirect('staff_visitors')

        visitor.status = 'OUT'
        visitor.out_time = timezone.now()
        visitor.save()

        for admin_user in User.objects.filter(role='ADMIN', is_active=True):
            create_notification(
                admin_user,
                title='Visitor Exit Marked by Staff',
                message=(
                    f'Visitor {visitor.name} exit marked for {visitor.visit_unit}.'
                ),
                notification_type='INFO',
                action_url='/management/visitors/',
                send_email=True,
                email_subject='Visitor Exit Marked',
            )

        messages.success(request, 'Visitor exit recorded!')
        return redirect('staff_visitors')
    
    return render(request, 'socity/staff/visitors_exit.html', {'visitor': visitor})


# ============= VISITOR REGISTRATION =============

@login_required
def visitor_registration(request):
    """Visitor registration form (guest/new visitor)"""
    if request.user.role != 'VISITOR':
        messages.error(request, 'This page is available for visitor accounts only.')
        return redirect('dashboard')

    recent_entries = _get_visitor_owned_entries(request.user)[:5]

    if request.method == 'POST':
        form = VisitorRegistrationForm(request.POST)
        if form.is_valid():
            visitor = form.save(commit=False)
            unit_no = (form.cleaned_data.get('unit_no') or '').strip()
            resolved_unit = _resolve_unit_from_input(unit_no)
            if resolved_unit:
                visitor.visit_unit = resolved_unit
                visitor.host = _get_active_host_for_unit(resolved_unit)
                # Link submitted entries to the logged-in visitor account identity.
                if request.user.email:
                    visitor.email = request.user.email
                if request.user.phone:
                    visitor.phone = request.user.phone
                if not visitor.email and request.user.email:
                    visitor.email = request.user.email
                visitor.save()

                for admin_user in User.objects.filter(role='ADMIN', is_active=True):
                    create_notification(
                        admin_user,
                        title='New Visitor Entry Registered',
                        message=(
                            f'Visitor {visitor.name}'
                            f'{f" ({visitor.email})" if visitor.email else ""} registered entry for {visitor.visit_unit} '
                            f'({visitor.purpose}).'
                        ),
                        notification_type='INFO',
                        action_url='/management/visitors/',
                        send_email=True,
                        email_subject='New Visitor Entry Registered',
                    )

                messages.success(request, 'Entry registered! Welcome!')
                request.session['visitor_setup_completed_once'] = True
                request.session['visitor_has_activity'] = True
                entry_url = reverse('socity:visitor_entry')
                # Use native Django redirect for full path+query URLs.
                return django_redirect(f"{entry_url}?visitor_id={visitor.id}")
            else:
                messages.error(request, 'Unit not found.')
    else:
        form = VisitorRegistrationForm(
            initial={'phone': request.user.phone or '', 'email': request.user.email or ''}
        )
    
    context = {
        'form': form,
        'recent_entries': recent_entries,
        'recent_notices': Notice.objects.filter(is_active=True).order_by('-posted_date')[:4],
    }
    return render(request, 'socity/visitor/entry_registration.html', context)


@login_required
def visitor_entry_form(request):
    """Visitor entry form (for checking in)"""
    if request.user.role != 'VISITOR':
        messages.error(request, 'This page is available for visitor accounts only.')
        return redirect('dashboard')

    visitor_id = request.GET.get('visitor_id')
    visitor = None
    if visitor_id:
        try:
            visitor = _get_visitor_owned_entries(request.user).get(id=visitor_id)
        except Visitor.DoesNotExist:
            visitor = None

    visitor_context = _build_visitor_dashboard_context(request)

    return render(
        request,
        'socity/visitor/entry_form.html',
        {
            'visitor': visitor,
            **visitor_context,
        },
    )



# Create your views here.

@login_required
def profile_view(request):
    """View user profile"""
    try:
        resident = Resident.objects.get(user=request.user)
    except Resident.DoesNotExist:
        resident = None
    
    context = {
        'resident': resident,
        'user': request.user
    }
    return render(request, 'core/profile.html', context)

@login_required
def profile_edit(request):
    """Edit user profile"""
    from core.forms import UserProfileForm
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile_view')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'core/profile_edit.html', {'form': form})

@login_required
def bills_view(request):
    """View maintenance bills"""
    try:
        resident = Resident.objects.get(user=request.user)
        billing_start = resident.move_in_date
        bills = MaintenanceBill.objects.filter(
            unit=resident.unit,
            billing_month__gte=billing_start,
        ).order_by('-billing_month')
        total_pending = bills.filter(status='PENDING').aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid = bills.filter(status='PAID').aggregate(Sum('amount'))['amount__sum'] or 0
        
        context = {
            'bills': bills,
            'total_pending': total_pending,
            'total_paid': total_paid,
            'resident': resident
        }
    except Resident.DoesNotExist:
        context = {'bills': [], 'total_pending': 0, 'total_paid': 0}
    
    return render(request, 'core/bills.html', context)

@login_required
def complaints_view(request):
    """View and manage complaints"""
    try:
        resident = Resident.objects.get(user=request.user)
        complaints = Complaint.objects.filter(raised_by=resident).order_by('-created_at')
    except Resident.DoesNotExist:
        complaints = []
    
    context = {'complaints': complaints}
    return render(request, 'core/complaints.html', context)

@login_required
def complaint_create(request):
    """Create a new complaint"""
    try:
        resident = Resident.objects.get(user=request.user)
    except Resident.DoesNotExist:
        messages.error(request, 'You need to have a resident profile to file a complaint.')
        return redirect('complaints_view')
    
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.raised_by = resident
            complaint.save()
            messages.success(request, 'Complaint filed successfully!')
            return redirect('complaints_view')
    else:
        form = ComplaintForm()
    
    return render(request, 'core/complaint_create.html', {'form': form})

@login_required
def legacy_complaint_detail(request, pk):
    """Legacy complaint detail view kept for backward compatibility."""
    try:
        resident = Resident.objects.get(user=request.user)
        complaint = get_object_or_404(Complaint, pk=pk, raised_by=resident)
    except Resident.DoesNotExist:
        return redirect('complaints_view')
    
    context = {'complaint': complaint}
    return render(request, 'core/complaint_detail.html', context)

@login_required
def amenities_view(request):
    """View available amenities"""
    amenities = Amenity.objects.filter(is_available=True)
    context = {'amenities': amenities}
    return render(request, 'core/amenities.html', context)

@login_required
def amenity_book(request):
    """Book an amenity"""
    try:
        resident = Resident.objects.get(user=request.user)
    except Resident.DoesNotExist:
        messages.error(request, 'You need to have a resident profile to book amenities.')
        return redirect('amenities_view')
    
    if request.method == 'POST':
        form = AmenityBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.resident = resident
            booking.save()
            messages.success(request, 'Amenity booked successfully! Awaiting confirmation.')
            return redirect('bookings_view')
    else:
        form = AmenityBookingForm()
    
    return render(request, 'core/amenity_book.html', {'form': form})

@login_required
def bookings_view(request):
    """View amenity bookings"""
    try:
        resident = Resident.objects.get(user=request.user)
        bookings = AmenityBooking.objects.filter(resident=resident).order_by('-booking_date')
    except Resident.DoesNotExist:
        bookings = []
    
    context = {'bookings': bookings}
    return render(request, 'core/bookings.html', context)

@login_required
def notices_view(request):
    """View society notices"""
    notices = [
        notice for notice in Notice.objects.filter(is_active=True).order_by('-posted_date')
        if notice.is_visible_to(request.user)
    ]
    context = {'notices': notices}
    return render(request, 'core/notices.html', context)

@login_required
def notice_detail(request, pk):
    """View notice details"""
    notice = get_object_or_404(Notice, pk=pk, is_active=True)
    context = {'notice': notice}
    return render(request, 'core/notice_detail.html', context)

@login_required
def transactions_view(request):
    """View payment history"""
    try:
        resident = Resident.objects.get(user=request.user)
        transactions = Transaction.objects.filter(resident=resident).order_by('-transaction_date')
        total_amount = transactions.aggregate(Sum('amount'))['amount__sum'] or 0
        
        context = {
            'transactions': transactions,
            'total_amount': total_amount,
            'resident': resident
        }
    except Resident.DoesNotExist:
        context = {'transactions': [], 'total_amount': 0}
    
    return render(request, 'core/transactions.html', context)

@login_required
def visitors_view(request):
    """View visitor log"""
    try:
        resident = Resident.objects.get(user=request.user)
        visitors = Visitor.objects.filter(host=resident).order_by('-in_time')
    except Resident.DoesNotExist:
        visitors = []
    
    context = {'visitors': visitors}
    return render(request, 'core/visitors.html', context)
