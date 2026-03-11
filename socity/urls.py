"""
URL Configuration for e-Society Management System - All Role-Based Features
path: socity/urls.py
"""

from django.urls import path
from . import views
from .views import (
    # Dashboard
    dashboard, admin_dashboard, resident_dashboard, staff_dashboard,
    
    # Admin - Resident Management
    resident_list, resident_detail, resident_edit, resident_delete,
    
    # Admin - Staff Management
    staff_list, staff_detail, staff_edit, staff_delete,
    
    # Admin - Property Management
    unit_list, unit_create, unit_edit, unit_delete,
    building_list, building_create, building_edit,
    
    # Admin - Billing
    bill_list, bill_create, bill_edit, bill_delete, bill_payment_history,
    
    # Admin - Complain Management
    complaint_list, complaint_detail, complaint_assign, complaint_close,
    
    # Admin - Notice Management
    notice_list, notice_create, notice_edit, notice_delete,
    
    # Admin - Amenities
    amenity_list, amenity_create, amenity_edit,
    amenity_booking_list, amenity_booking_approve,
    
    # Admin - Visitor Management
    visitor_list,
    
    # Resident Features
    resident_bills_view, resident_payment_view,
    resident_complaint_list, resident_complaint_create, resident_complaint_detail,
    resident_amenities_view, resident_amenity_book, resident_booking_list,
    resident_notice_list, resident_notice_detail,
    resident_visitor_approval, resident_visitor_list,
    resident_profile_view, resident_profile_edit,
    
    # Staff Features
    staff_task_list, staff_task_update,
    staff_complaint_list, staff_complaint_status_update,
    staff_visitor_list, staff_visitor_entry, staff_visitor_exit,
    
    # Visitor Features
    visitor_registration, visitor_entry_form,
)

app_name = 'socity'

urlpatterns = [
    # Dashboard
    path('dashboard/', dashboard, name='dashboard'),
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
    path('resident/dashboard/', resident_dashboard, name='resident_dashboard'),
    path('staff/dashboard/', staff_dashboard, name='staff_dashboard'),
    
    # ============= ADMIN URLS =============
    
    # Resident Management
    path('admin/residents/', resident_list, name='resident_list'),
    path('admin/residents/<int:resident_id>/', resident_detail,  name='resident_detail'),
    path('admin/residents/<int:resident_id>/edit/', resident_edit, name='resident_edit'),
    path('admin/residents/<int:resident_id>/delete/', resident_delete, name='resident_delete'),
    
    # Staff Management
    path('admin/staff/', staff_list, name='staff_list'),
    path('admin/staff/<int:staff_id>/', staff_detail, name='staff_detail'),
    path('admin/staff/<int:staff_id>/edit/', staff_edit, name='staff_edit'),
    path('admin/staff/<int:staff_id>/delete/', staff_delete, name='staff_delete'),
    
    # Unit/Property Management
    path('admin/units/', unit_list, name='unit_list'),
    path('admin/units/create/', unit_create, name='unit_create'),
    path('admin/units/<int:unit_id>/edit/', unit_edit, name='unit_edit'),
    path('admin/units/<int:unit_id>/delete/', unit_delete, name='unit_delete'),
    
    # Building Management
    path('admin/buildings/', building_list, name='building_list'),
    path('admin/buildings/create/', building_create, name='building_create'),
    path('admin/buildings/<int:building_id>/edit/', building_edit, name='building_edit'),
    
    # Maintenance Billing
    path('admin/bills/', bill_list, name='bill_list'),
    path('admin/bills/create/', bill_create, name='bill_create'),
    path('admin/bills/<int:bill_id>/edit/', bill_edit, name='bill_edit'),
    path('admin/bills/<int:bill_id>/delete/', bill_delete, name='bill_delete'),
    path('admin/bills/payment-history/', bill_payment_history, name='bill_payment_history'),
    
    # Complaint Management
    path('admin/complaints/', complaint_list, name='complaint_list'),
    path('admin/complaints/<int:complaint_id>/', complaint_detail, name='complaint_detail'),
    path('admin/complaints/<int:complaint_id>/assign/', complaint_assign, name='complaint_assign'),
    path('admin/complaints/<int:complaint_id>/close/', complaint_close, name='complaint_close'),
    
    # Notice Management
    path('admin/notices/', notice_list, name='notice_list'),
    path('admin/notices/create/', notice_create, name='notice_create'),
    path('admin/notices/<int:notice_id>/edit/', notice_edit, name='notice_edit'),
    path('admin/notices/<int:notice_id>/delete/', notice_delete, name='notice_delete'),
    
    # Amenities Management
    path('admin/amenities/', amenity_list, name='amenity_list'),
    path('admin/amenities/create/', amenity_create, name='amenity_create'),
    path('admin/amenities/<int:amenity_id>/edit/', amenity_edit, name='amenity_edit'),
    path('admin/amenities/bookings/', amenity_booking_list, name='amenity_booking_list'),
    path('admin/amenities/bookings/<int:booking_id>/approve/', amenity_booking_approve, name='amenity_booking_approve'),
    
    # Visitor Management
    path('admin/visitors/', visitor_list, name='visitor_list'),
    
    # ============= RESIDENT URLS =============
    
    # Profile
    path('resident/profile/', resident_profile_view, name='resident_profile'),
    path('resident/profile/edit/', resident_profile_edit, name='resident_profile_edit'),
    
    # Bills & Payments
    path('resident/bills/', resident_bills_view, name='resident_bills'),
    path('resident/bills/<int:bill_id>/pay/', resident_payment_view, name='resident_payment'),
    
    # Complaints
    path('resident/complaints/', resident_complaint_list, name='resident_complaints'),
    path('resident/complaints/create/', resident_complaint_create, name='resident_complaint_create'),
    path('resident/complaints/<int:complaint_id>/', resident_complaint_detail, name='resident_complaint_detail'),
    
    # Amenities
    path('resident/amenities/', resident_amenities_view, name='resident_amenities'),
    path('resident/amenities/<int:amenity_id>/book/', resident_amenity_book, name='resident_amenity_book'),
    path('resident/bookings/', resident_booking_list, name='resident_bookings'),
    
    # Notices
    path('resident/notices/', resident_notice_list, name='resident_notices'),
    path('resident/notices/<int:notice_id>/', resident_notice_detail, name='resident_notice_detail'),
    
    # Visitor Management
    path('resident/visitor-approvals/', resident_visitor_approval, name='resident_visitor_approvals'),
    path('resident/visitor-log/', resident_visitor_list, name='resident_visitor_log'),
    
    # ============= STAFF URLS =============
    
    # Tasks
    path('staff/tasks/', staff_task_list, name='staff_tasks'),
    path('staff/tasks/<int:task_id>/update/', staff_task_update, name='staff_task_update'),
    
    # Complaints
    path('staff/complaints/', staff_complaint_list, name='staff_complaints'),
    path('staff/complaints/<int:complaint_id>/status/', staff_complaint_status_update, name='staff_complaint_status'),
    
    # Visitor Management
    path('staff/visitors/', staff_visitor_list, name='staff_visitors'),
    path('staff/visitors/entry/', staff_visitor_entry, name='staff_visitor_entry'),
    path('staff/visitors/<int:visitor_id>/exit/', staff_visitor_exit, name='staff_visitor_exit'),
    
    # ============= VISITOR URLS =============
    
    # Visitor Entry/Exit
    path('visitor/register/', visitor_registration, name='visitor_registration'),
    path('visitor/entry/', visitor_entry_form, name='visitor_entry'),
]
