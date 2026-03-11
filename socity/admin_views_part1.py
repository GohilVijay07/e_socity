"""
ADMIN VIEWS - Comprehensive Admin Role Features
"""

# ============= DASHBOARD =============

@login_required
def dashboard(request):
    """Role-based dashboard view"""
    user = request.user
    
    if user.role == 'ADMIN':
        return admin_dashboard(request)
    elif user.role == 'RESIDENT':
        return resident_dashboard(request)
    elif user.role == 'STAFF':
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
        'total_unpaid_amount': MaintenanceBill.objects.filter(status__in=['PENDING', 'OVERDUE']).aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
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
        'pending_bills': MaintenanceBill.objects.filter(unit=resident.unit, status='PENDING').count(),
        'total_bill_amount': MaintenanceBill.objects.filter(unit=resident.unit, status='PENDING').aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
        'paid_bills': MaintenanceBill.objects.filter(unit=resident.unit, status='PAID').count(),
        'my_complaints': Complaint.objects.filter(raised_by=resident).order_by('-created_at')[:5],
        'open_complaints': Complaint.objects.filter(raised_by=resident, status='OPEN').count(),
        'my_bookings': AmenityBooking.objects.filter(resident=resident).order_by('-booking_date')[:5],
        'pending_bookings': AmenityBooking.objects.filter(resident=resident, status='PENDING').count(),
        'notices': Notice.objects.filter(is_active=True).order_by('-posted_date')[:5],
        'today_visitors': Visitor.objects.filter(visit_unit=resident.unit, in_time__date=timezone.now().date()).count(),
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


# ============= RESIDENT MANAGEMENT =============

@admin_required
def resident_list(request):
    """List all residents with search and filter"""
    search_query = request.GET.get('search', '')
    unit_filter = request.GET.get('unit', '')
    status_filter = request.GET.get('status', '')
    
    residents = Resident.objects.select_related('user', 'unit').all()
    
    if search_query:
        residents = residents.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(unit__unit_no__icontains=search_query)
        )
    
    if unit_filter:
        residents = residents.filter(unit__unit_no=unit_filter)
    
    if status_filter:
        residents = residents.filter(status=status_filter)
    
    context = {
        'residents': residents,
        'search_query': search_query,
        'units': Unit.objects.all(),
        'status_choices': Resident.STATUS_CHOICES,
    }
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
    """Edit resident details"""
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


# ============= STAFF MANAGEMENT =============

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
    
    context = {
        'staff_members': staff_members,
        'search_query': search_query,
        'designation_choices': Staff.DESIGNATION_CHOICES,
        'status_choices': Staff.STATUS_CHOICES,
    }
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
    """Edit staff member details"""
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
