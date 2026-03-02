from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # Password reset URLs (OTP-based)
    path('password-reset/', views.password_reset_otp_request_view, name='password_reset'),
    path('password-reset/otp-verify/', views.password_reset_otp_verify_view, name='password_reset_otp_verify'),
    
    # Contact form URL
    path('contact/', views.contact_view, name='contact'),
]
