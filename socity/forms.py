from django import forms
from .models import (
    Complaint, AmenityBooking, Notice, MaintenanceBill, Resident, 
    Staff, Unit, Building, Amenity, Task, Visitor, VisitorApproval,
    ComplaintUpdate, Transaction
)
from core.models import User


# ============= ADMIN FORMS =============

class ResidentForm(forms.ModelForm):
    """Form for admin to create/edit residents"""
    class Meta:
        model = Resident
        fields = ['unit', 'status', 'vehicle_no', 'member_count', 'move_in_date', 'move_out_date', 'emergency_contact', 'emergency_phone', 'occupation']
        widgets = {
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'vehicle_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vehicle Number'}),
            'member_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'move_in_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'move_out_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency Contact Name'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency Phone'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Occupation'}),
        }


class StaffForm(forms.ModelForm):
    """Form for admin to create/edit staff members"""
    class Meta:
        model = Staff
        fields = ['designation', 'department', 'status', 'join_date', 'salary', 'aadhar_no', 'emergency_contact', 'emergency_phone', 'address']
        widgets = {
            'designation': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'join_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Salary'}),
            'aadhar_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Aadhar Number'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency Contact'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency Phone'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3}),
        }


class UnitForm(forms.ModelForm):
    """Form for admin to create/edit units/flats"""
    class Meta:
        model = Unit
        fields = ['unit_no', 'wing', 'floor', 'unit_type', 'sq_ft', 'is_occupied']
        widgets = {
            'unit_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unit Number'}),
            'wing': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Wing'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'unit_type': forms.Select(attrs={'class': 'form-control'}),
            'sq_ft': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Square Feet', 'step': '0.01'}),
            'is_occupied': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BuildingForm(forms.ModelForm):
    """Form for admin to create/edit buildings"""
    class Meta:
        model = Building
        fields = ['name', 'wing_code', 'total_floors', 'units_per_floor', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Building Name'}),
            'wing_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Wing Code'}),
            'total_floors': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'units_per_floor': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Building Address', 'rows': 3}),
        }


class MaintenanceBillForm(forms.ModelForm):
    """Form for admin to create/edit maintenance bills"""
    class Meta:
        model = MaintenanceBill
        fields = ['unit', 'billing_month', 'amount', 'penalty', 'status']
        widgets = {
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'billing_month': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount', 'step': '0.01'}),
            'penalty': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Penalty', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class NoticeForm(forms.ModelForm):
    """Form for admin/staff to create/update notices"""
    class Meta:
        model = Notice
        fields = ['title', 'content', 'priority', 'expiry_date', 'image', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Notice Title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Notice Content', 'rows': 6}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AmenityForm(forms.ModelForm):
    """Form for admin to create/edit amenities"""
    class Meta:
        model = Amenity
        fields = ['name', 'description', 'is_available', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Amenity Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Description', 'rows': 3}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class AmenityBookingApprovalForm(forms.ModelForm):
    """Form for admin to approve/reject amenity bookings"""
    class Meta:
        model = AmenityBooking
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class ComplaintStatusForm(forms.ModelForm):
    """Form for admin/staff to update complaint status"""
    class Meta:
        model = Complaint
        fields = ['status', 'assigned_to']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
        }


# ============= RESIDENT FORMS =============

class ComplaintForm(forms.ModelForm):
    """Form for resident to file complaints"""
    class Meta:
        model = Complaint
        fields = ['category', 'title', 'description', 'priority']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Complaint Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Describe your complaint...', 'rows': 5}),
            'priority': forms.Select(attrs={'class': 'form-control'}, choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')]),
        }


class AmenityBookingForm(forms.ModelForm):
    """Form for resident to book amenities"""
    class Meta:
        model = AmenityBooking
        fields = ['amenity', 'booking_date', 'start_time', 'end_time', 'purpose']
        widgets = {
            'amenity': forms.Select(attrs={'class': 'form-control'}),
            'booking_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Purpose of booking'}),
        }


class PaymentForm(forms.ModelForm):
    """Form for residents to record maintenance bill payments"""
    class Meta:
        model = Transaction
        fields = ['amount', 'payment_mode', 'reference_no', 'remarks']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Payment Amount', 'step': '0.01'}),
            'payment_mode': forms.Select(attrs={'class': 'form-control'}),
            'reference_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference/Cheque/Transaction Number'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Additional remarks', 'rows': 3}),
        }


class VisitorApprovalForm(forms.ModelForm):
    """Form for residents to pre-approve visitors"""
    class Meta:
        model = VisitorApproval
        fields = ['visitor_name', 'visitor_phone', 'purpose', 'status', 'valid_from', 'valid_to', 'notes']
        widgets = {
            'visitor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Visitor Name'}),
            'visitor_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Visitor Phone'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Purpose of Visit'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'valid_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_to': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Additional notes', 'rows': 3}),
        }


class ResidentProfileForm(forms.ModelForm):
    """Form for resident to update their profile"""
    class Meta:
        model = Resident
        fields = ['vehicle_no', 'member_count', 'emergency_contact', 'emergency_phone', 'occupation']
        widgets = {
            'vehicle_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vehicle Number'}),
            'member_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency Contact Name'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency Phone'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Occupation'}),
        }


# ============= STAFF FORMS =============

class TaskForm(forms.ModelForm):
    """Form for admin/staff to assign tasks"""
    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'location', 'priority', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Task Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Task Description', 'rows': 4}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class TaskUpdateForm(forms.ModelForm):
    """Form for staff to update task status"""
    class Meta:
        model = Task
        fields = ['status', 'remarks', 'completed_date']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Work completed remarks', 'rows': 3}),
            'completed_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }


# ============= VISITOR FORMS =============

class VisitorRegistrationForm(forms.ModelForm):
    """Form for visitor entry registration"""
    unit_no = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unit/Flat Number'})
    )
    
    class Meta:
        model = Visitor
        fields = ['name', 'phone', 'purpose', 'vehicle_no']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Visitor Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Purpose of Visit'}),
            'vehicle_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vehicle Number (if any)'}),
        }


class VisitorExitForm(forms.Form):
    """Form for recording visitor exit"""
    out_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        required=False
    )


class ComplaintUpdateForm(forms.ModelForm):
    """Form for updating complaint status with remarks"""
    class Meta:
        model = ComplaintUpdate
        fields = ['status', 'remarks']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Status update remarks', 'rows': 3}),
        }
