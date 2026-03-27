from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),

    # Password reset URLs (OTP-based)
    path('password-reset/', views.password_reset_otp_request_view, name='password_reset'),
    path('password-reset/otp-verify/', views.password_reset_otp_verify_view, name='password_reset_otp_verify'),
    path('email-verify/<uuid:token>/', views.email_verify_view, name='email_verify'),
    path('email-verify/resend/', views.resend_verification_email_view, name='resend_verification_email'),

    # In-app notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.notification_read_view, name='notification_read'),
    path('notifications/read-all/', views.notifications_mark_all_read_view, name='notifications_mark_all_read'),
    
    # Contact form URL
    path('contact/', views.contact_view, name='contact'),
]
