"""
URL configuration for e_socity project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views
from socity import views as socity_views

urlpatterns = [
    path('', core_views.home, name='home'),
    path('admin/', admin.site.urls),
    path('signup/', core_views.userSignupView, name='signup'),
    path('login/', core_views.userLoginView, name='login'),
    path('logout/', core_views.userLogoutView, name='logout'),
    path('dashboard/', core_views.dashboard, name='dashboard'),
    
    # User profile URLs
    path('profile/', socity_views.profile_view, name='profile_view'),
    path('profile/edit/', socity_views.profile_edit, name='profile_edit'),
    
    # Bills URLs
    path('bills/', socity_views.bills_view, name='bills_view'),
    
    # Complaints URLs
    path('complaints/', socity_views.complaints_view, name='complaints_view'),
    path('complaints/create/', socity_views.complaint_create, name='complaint_create'),
    path('complaints/<int:pk>/', socity_views.complaint_detail, name='complaint_detail'),
    
    # Amenities URLs
    path('amenities/', socity_views.amenities_view, name='amenities_view'),
    path('amenities/book/', socity_views.amenity_book, name='amenity_book'),
    path('bookings/', socity_views.bookings_view, name='bookings_view'),
    
    # Notices URLs
    path('notices/', socity_views.notices_view, name='notices_view'),
    path('notices/<int:pk>/', socity_views.notice_detail, name='notice_detail'),
    
    # Transactions/Payments URLs
    path('transactions/', socity_views.transactions_view, name='transactions_view'),
    
    # Visitors URLs
    path('visitors/', socity_views.visitors_view, name='visitors_view'),
    
    path('core/', include('core.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
