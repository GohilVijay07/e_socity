from django import forms
from .models import Complaint, AmenityBooking

class ComplaintForm(forms.ModelForm):
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
