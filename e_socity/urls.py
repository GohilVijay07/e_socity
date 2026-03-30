"""
URL configuration for e_socity project.
Main URL dispatcher for all app URLs
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views

urlpatterns = [
    # Home & Authentication
    path('', core_views.home, name='home'),
    path('signup/', core_views.userSignupView, name='signup'),
    path('signup/otp-verify/', core_views.signup_otp_verify_view, name='signup_otp_verify'),
    path('login/', core_views.userLoginView, name='login'),
    path('logout/', core_views.userLogoutView, name='logout'),
    path('dashboard/', core_views.dashboard, name='dashboard'),
    
    # Admin Panel
    path('admin/', admin.site.urls),
    
    # Core App URLs (Password Reset, Contact, etc.)
    path('core/', include('core.urls')),
    
    # Society Management URLs (All role-based features)
    # Includes: Admin management, Resident features, Staff tasks, Visitor registration
    path('', include('socity.urls', namespace='socity')),
]

# Error handlers
handler403 = 'core.views.error_403'
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

