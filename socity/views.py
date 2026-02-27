from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from .models import (
    Resident, MaintenanceBill, Complaint, Visitor, 
    Amenity, AmenityBooking, Notice, Transaction
)
from .forms import ComplaintForm, AmenityBookingForm
from core.models import User

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
