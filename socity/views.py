"""
Role-based Views for e-Society Management System
Handles all views for Admin, Resident, Staff, and Visitor functionalities
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from core.decorators import (
    role_required, admin_required, resident_required, 
    staff_required, multiple_roles_required
)
from core.models import User
from .models import (
    Unit, Resident, Staff, MaintenanceBill, Visitor, Complaint, 
    Amenity, AmenityBooking, Notice, Transaction, Building, 
    Task, VisitorApproval, ComplaintUpdate
)
from .forms import (
    ResidentForm, StaffForm, UnitForm, BuildingForm, MaintenanceBillForm,
    NoticeForm, AmenityForm, AmenityBookingApprovalForm, ComplaintStatusForm,
    ComplaintForm, AmenityBookingForm, PaymentForm, VisitorApprovalForm,
    ResidentProfileForm, TaskForm, TaskUpdateForm, VisitorRegistrationForm,
    VisitorExitForm, ComplaintUpdateForm
)


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
    else:
        return render(request, 'core/dashboard.html')


@admin_required
def admin_dashboard(request):
    """Admin dashboard with system statistics"""
    context = {
        'total_residents': Resident.objects.count(),
        'total_staff': Staff.objects.count(),
        'total_units': Unit.objects.count(),
        'occupied_units': Unit.objects.filter(is_occupied=True).count(),
        'total_complaints': Complaint.objects.count(),
        'open_complaints': Complaint.objects.filter(status='OPEN').count(),
        'in_progress_complaints': Complaint.objects.filter(status='IN_PROGRESS').count(),
        'total_pending_bills': MaintenanceBill.objects.filter(status='PENDING').count(),
        'total_unpaid_amount': MaintenanceBill.objects.filter(
            status__in=['PENDING', 'OVERDUE']
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
        'total_paid_bills': MaintenanceBill.objects.filter(status='PAID').count(),
        'today_visitors': Visitor.objects.filter(in_time__date=timezone.now().date()).count(),
        'pending_amenity_bookings': AmenityBooking.objects.filter(status='PENDING').count(),
        'total_amenities': Amenity.objects.count(),
        'recent_complaints': Complaint.objects.all()[:5],
        'recent_notices': Notice.objects.all()[:5],
        'recent_visitors': Visitor.objects.all()[:10],
    }
    return render(request, 'socity/admin/admin_dashboard.html', context)


@resident_required
def resident_dashboard(request):
    """Resident dashboard with personal information"""
    try:
        resident = request.user.resident_profile
    except:
        messages.error(request, 'Resident profile not found.')
        return redirect('home')
    
    context = {
        'resident': resident,
        'unit': resident.unit,
        'pending_bills': MaintenanceBill.objects.filter(
            unit=resident.unit, status='PENDING'
        ).count(),
        'total_bill_amount': MaintenanceBill.objects.filter(
            unit=resident.unit, status='PENDING'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
        'paid_bills': MaintenanceBill.objects.filter(unit=resident.unit, status='PAID').count(),
        'my_complaints': Complaint.objects.filter(raised_by=resident).order_by('-created_at')[:5],
        'open_complaints': Complaint.objects.filter(raised_by=resident, status='OPEN').count(),
        'my_bookings': AmenityBooking.objects.filter(resident=resident).order_by('-booking_date')[:5],
        'pending_bookings': AmenityBooking.objects.filter(resident=resident, status='PENDING').count(),
        'notices': Notice.objects.filter(is_active=True).order_by('-posted_date')[:5],
        'today_visitors': Visitor.objects.filter(
            visit_unit=resident.unit, in_time__date=timezone.now().date()
        ).count(),
    }
    return render(request, 'socity/resident/resident_dashboard.html', context)


@staff_required
def staff_dashboard(request):
    """Staff dashboard with assigned tasks and visitors"""
    try:
        staff = request.user.staff_profile
    except:
        messages.error(request, 'Staff profile not found.')
        return redirect('home')
    
    context = {
        'staff': staff,
        'assigned_tasks': Task.objects.filter(assigned_to=staff).order_by('-assigned_date')[:5],
        'pending_tasks': Task.objects.filter(assigned_to=staff, status='PENDING').count(),
        'in_progress_tasks': Task.objects.filter(assigned_to=staff, status='IN_PROGRESS').count(),
        'assigned_complaints': Complaint.objects.filter(assigned_to=request.user).order_by('-created_at')[:5],
        'today_visitors': Visitor.objects.filter(in_time__date=timezone.now().date()).count(),
        'pending_visitor_exits': Visitor.objects.filter(status='IN').count(),
    }
    return render(request, 'socity/staff/staff_dashboard.html', context)


# ============= ADMIN: RESIDENT MANAGEMENT =============

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
    
    bills = MaintenanceBill.objects.select_related('unit').all()
    
    if search_query:
        bills = bills.filter(Q(unit__unit_no__icontains=search_query) | Q(unit__wing__icontains=search_query))
    if status_filter:
        bills = bills.filter(status=status_filter)
    
    context = {'bills': bills, 'search_query': search_query, 'status_choices': MaintenanceBill.PAYMENT_STATUS_CHOICES,
               'total_pending_amount': bills.filter(status='PENDING').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')}
    return render(request, 'socity/admin/bill_list.html', context)


@admin_required
def bill_create(request):
    """Create new maintenance bill"""
    if request.method == 'POST':
        form = MaintenanceBillForm(request.POST)
        if form.is_valid():
            form.save()
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
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    
    complaints = Complaint.objects.select_related('raised_by', 'assigned_to').all()
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    if category_filter:
        complaints = complaints.filter(category=category_filter)
    
    context = {'complaints': complaints, 'status_choices': Complaint.STATUS_CHOICES,
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
def complaint_assign(request, complaint_id):
    """Assign complaint to staff"""
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.method == 'POST':
        staff_user_id = request.POST.get('assigned_to')
        if staff_user_id:
            staff_user = get_object_or_404(User, id=staff_user_id, role='STAFF')
            complaint.assigned_to = staff_user
            complaint.status = 'IN_PROGRESS'
            complaint.save()
            
            # Create task for staff
            Task.objects.create(
                title=f"Resolve: {complaint.title}",
                description=complaint.description,
                assigned_to=staff_user.staff_profile,
                assigned_by=request.user,
                complaint=complaint,
                priority=complaint.priority,
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
        complaint.status = 'CLOSED'
        complaint.resolved_date = timezone.now()
        complaint.save()
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
    
    visitors = Visitor.objects.select_related('visit_unit', 'host').all()
    if search_query:
        visitors = visitors.filter(Q(name__icontains=search_query) | Q(phone__icontains=search_query))
    if status_filter:
        visitors = visitors.filter(status=status_filter)
    
    context = {'visitors': visitors, 'search_query': search_query, 'status_choices': Visitor.STATUS_CHOICES,
               'today_visitors': Visitor.objects.filter(in_time__date=timezone.now().date()).count()}
    return render(request, 'socity/admin/visitor_list.html', context)


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
    
    bills = MaintenanceBill.objects.filter(unit=resident.unit).order_by('-billing_month')
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
    
    bill = get_object_or_404(MaintenanceBill, id=bill_id, unit=resident.unit)
    if bill.status == 'PAID':
        messages.info(request, 'This bill has already been paid.')
        return redirect('resident_bills')
    
    if request.method == 'POST':
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
        form = PaymentForm(initial={'amount': bill.amount})
    
    return render(request, 'socity/resident/bills_pay.html', {'form': form, 'bill': bill})


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
            complaint.save()
            messages.success(request, 'Complaint filed successfully!')
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
def resident_notice_list(request):
    """View society notices"""
    notices = Notice.objects.filter(is_active=True).order_by('-posted_date')
    return render(request, 'socity/resident/notices_list.html', {'notices': notices})


@resident_required
def resident_notice_detail(request, notice_id):
    """View notice details"""
    notice = get_object_or_404(Notice, id=notice_id, is_active=True)
    return render(request, 'socity/resident/notices_detail.html', {'notice': notice})


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
    
    visitors = Visitor.objects.filter(visit_unit=resident.unit).order_by('-in_time')
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
    complaints = Complaint.objects.filter(assigned_to=request.user).order_by('-created_at')
    return render(request, 'socity/staff/complaints_list.html', {'complaints': complaints})


@staff_required
def staff_complaint_status_update(request, complaint_id):
    """Update complaint status"""
    complaint = get_object_or_404(Complaint, id=complaint_id, assigned_to=request.user)
    
    if request.method == 'POST':
        form = ComplaintUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.complaint = complaint
            update.updated_by = request.user
            update.save()
            
            complaint.status = form.cleaned_data['status']
            complaint.save()
            
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
    
    visitors = Visitor.objects.all()
    if date_filter:
        visitors = visitors.filter(in_time__date=date_filter)
    if status_filter:
        visitors = visitors.filter(status=status_filter)
    
    return render(request, 'socity/staff/visitors_list.html', {'visitors': visitors, 'status_choices': Visitor.STATUS_CHOICES})


@staff_required
def staff_visitor_entry(request):
    """Register visitor entry"""
    if request.method == 'POST':
        form = VisitorRegistrationForm(request.POST)
        if form.is_valid():
            visitor = form.save(commit=False)
            unit_no = form.cleaned_data.get('unit_no')
            try:
                visitor.visit_unit = Unit.objects.get(unit_no=unit_no)
                visitor.save()
                messages.success(request, 'Visitor entry registered!')
                return redirect('staff_visitors')
            except Unit.DoesNotExist:
                messages.error(request, 'Unit not found.')
    else:
        form = VisitorRegistrationForm()
    
    return render(request, 'socity/staff/visitors_entry.html', {'form': form})


@staff_required
def staff_visitor_exit(request, visitor_id):
    """Record visitor exit"""
    visitor = get_object_or_404(Visitor, id=visitor_id)
    
    if request.method == 'POST':
        visitor.status = 'OUT'
        visitor.out_time = timezone.now()
        visitor.save()
        messages.success(request, 'Visitor exit recorded!')
        return redirect('staff_visitors')
    
    return render(request, 'socity/staff/visitors_exit.html', {'visitor': visitor})


# ============= VISITOR REGISTRATION =============

@login_required
def visitor_registration(request):
    """Visitor registration form (guest/new visitor)"""
    if request.method == 'POST':
        form = VisitorRegistrationForm(request.POST)
        if form.is_valid():
            visitor = form.save(commit=False)
            unit_no = form.cleaned_data.get('unit_no')
            try:
                visitor.visit_unit = Unit.objects.get(unit_no=unit_no)
                visitor.save()
                messages.success(request, 'Entry registered! Welcome!')
                return redirect('visitor_entry')
            except Unit.DoesNotExist:
                messages.error(request, 'Unit not found.')
    else:
        form = VisitorRegistrationForm()
    
    return render(request, 'socity/visitor/entry_registration.html', {'form': form})


@login_required
def visitor_entry_form(request):
    """Visitor entry form (for checking in)"""
    return render(request, 'socity/visitor/entry_form.html')



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
        bills = MaintenanceBill.objects.filter(unit=resident.unit).order_by('-billing_month')
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
def complaint_detail(request, pk):
    """View complaint details"""
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
    notices = Notice.objects.filter(is_active=True).order_by('-posted_date')
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
