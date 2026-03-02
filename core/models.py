from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import random
import string

# 1. Custom User Model - CORE (Only Authentication)
class User(AbstractUser):
    """Custom User model for e-society management system"""
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('RESIDENT', 'Resident'),
        ('VISITOR', 'Visitor'),
        ('STAFF', 'Staff'),
    ]
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('P', 'Prefer not to say'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='RESIDENT')
    phone = models.CharField(max_length=15, blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    is_active_resident = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"


# 2. OTP Model for Password Reset
class PasswordResetOTP(models.Model):
    """Model to store OTP for password reset"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_otps')
    otp = models.CharField(max_length=6, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"OTP for {self.user.email} - {'Used' if self.is_used else 'Valid'}"
    
    def is_valid(self):
        """Check if OTP is valid (not expired and not used)"""
        return not self.is_used and timezone.now() < self.expires_at
    
    @staticmethod
    def generate_otp():
        """Generate a 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def create_otp(user, validity_minutes=10):
        """Create a new OTP for user (invalidate previous unused OTPs)"""
        # Invalidate previous unused OTPs
        PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Create new OTP
        otp = PasswordResetOTP.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=validity_minutes)
        
        otp_obj = PasswordResetOTP.objects.create(
            user=user,
            otp=otp,
            expires_at=expires_at
        )
        return otp_obj
    
    class Meta:
        ordering = ['-created_at']