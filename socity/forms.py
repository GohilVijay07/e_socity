from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import (
    Complaint, AmenityBooking, Notice, MaintenanceBill, Resident, 
    Staff, Unit, Building, Amenity, Task, Visitor, VisitorApproval,
    ComplaintUpdate, Transaction
)
from core.models import User


class _AdminUserCreateMixin:
    """Shared helpers for admin-created user accounts."""

    @staticmethod
    def build_unique_username(email):
        base = email.split('@')[0].strip().lower() or 'user'
        username = base
        suffix = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{suffix}"
            suffix += 1
        return username


class AdminUserCreateForm(UserCreationForm):
    """Admin form for creating any user and assigning role/active status."""
    role = forms.ChoiceField(
        choices=[('ADMIN', 'Administrator'), ('RESIDENT', 'Resident'), ('STAFF', 'Security/Staff'), ('VISITOR', 'Visitor')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_active = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'gender', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
        }


class AdminUserUpdateForm(forms.ModelForm):
    """Admin form for updating user profile and role."""
    role = forms.ChoiceField(
        choices=[('ADMIN', 'Administrator'), ('RESIDENT', 'Resident'), ('STAFF', 'Security/Staff'), ('VISITOR', 'Visitor')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'gender', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AdminResidentCreateForm(forms.Form, _AdminUserCreateMixin):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    gender = forms.ChoiceField(required=False, choices=User.GENDER_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    unit = forms.ModelChoiceField(queryset=Unit.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    status = forms.ChoiceField(choices=Resident.STATUS_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    vehicle_no = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    member_count = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    move_in_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    emergency_contact = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    emergency_phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    occupation = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email


class AdminStaffCreateForm(forms.Form, _AdminUserCreateMixin):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    gender = forms.ChoiceField(required=False, choices=User.GENDER_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    designation = forms.ChoiceField(choices=Staff.DESIGNATION_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    department = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    status = forms.ChoiceField(choices=Staff.STATUS_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    join_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    salary = forms.DecimalField(required=False, max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    emergency_contact = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    emergency_phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email


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
        fields = ['unit', 'billing_month', 'bill_date', 'amount', 'penalty', 'status']
        widgets = {
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'billing_month': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'bill_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'placeholder': 'Leave empty to use billing_month'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount', 'step': '0.01'}),
            'penalty': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Penalty', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        """Validate that bill_date doesn't precede when the unit had residents."""
        cleaned_data = super().clean()
        unit = cleaned_data.get('unit')
        bill_date = cleaned_data.get('bill_date')
        billing_month = cleaned_data.get('billing_month')
        
        # If bill_date is not set, use billing_month as the effective date
        effective_date = bill_date if bill_date else billing_month
        
        if effective_date and unit:
            # Check if there's any resident for this unit at the effective date
            from django.db.models import Q
            from .models import Resident
            
            eligible_residents = Resident.objects.filter(
                unit=unit,
                move_in_date__lte=effective_date,
            ).filter(
                Q(move_out_date__isnull=True) | Q(move_out_date__gte=effective_date)
            )
            
            if not eligible_residents.exists():
                raise forms.ValidationError(
                    f'No resident was living in {unit} on or before {effective_date.strftime("%Y-%m-%d")}. '
                    'Bill date must align with when the unit had active residents.'
                )
        
        return cleaned_data


class NoticeForm(forms.ModelForm):
    """Form for admin/staff to create/update notices"""
    SEND_TARGET_CHOICES = [
        ('ALL', 'All Users'),
        ('SELECTED', 'Selected Users'),
    ]

    send_target = forms.ChoiceField(
        choices=SEND_TARGET_CHOICES,
        initial='ALL',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': 8})
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipients'].queryset = User.objects.filter(role__in=['ADMIN', 'RESIDENT', 'STAFF']).order_by('first_name', 'last_name', 'username')
        if self.instance and self.instance.pk:
            selected_users = User.objects.filter(notice_recipients__notice=self.instance)
            self.fields['recipients'].initial = selected_users
            self.fields['send_target'].initial = 'SELECTED' if selected_users.exists() else 'ALL'

    def clean(self):
        cleaned_data = super().clean()
        send_target = cleaned_data.get('send_target')
        recipients = cleaned_data.get('recipients')
        if send_target == 'SELECTED' and not recipients:
            self.add_error('recipients', 'Please select at least one user.')
        return cleaned_data


class AdminComplaintUpdateForm(forms.Form):
    """Admin workflow form for complaint status, assignment, and comments."""
    status = forms.ChoiceField(
        choices=[('OPEN', 'Pending'), ('IN_PROGRESS', 'In Progress'), ('RESOLVED', 'Resolved')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(role='STAFF', is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Admin comments'})
    )


class VisitorApprovalActionForm(forms.Form):
    """Approve/reject visitor entries from admin panel."""
    action = forms.ChoiceField(
        choices=[('APPROVED', 'Approve'), ('REJECTED', 'Reject')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    approval_note = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason or notes'})
    )


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
        fields = ['name', 'phone', 'email', 'purpose', 'vehicle_no']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Visitor Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email (optional)'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Purpose of Visit'}),
            'vehicle_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vehicle Number (if any)'}),
        }

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        normalized = ''.join(ch for ch in phone if ch.isdigit())
        if len(normalized) < 10:
            raise forms.ValidationError('Enter a valid phone number with at least 10 digits.')
        return normalized

    def clean_unit_no(self):
        unit_no = (self.cleaned_data.get('unit_no') or '').strip()
        if not unit_no:
            raise forms.ValidationError('Unit / Flat Number is required.')
        return unit_no


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
