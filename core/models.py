from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

# 1. Custom User Model - CORE (Only Authentication)
class User(AbstractUser):
    """Custom User model for e-society management system"""
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('RESIDENT', 'Resident'),
        ('VISITOR', 'Visitor'),
        ('STAFF', 'Staff'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='RESIDENT')
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    is_active_resident = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"