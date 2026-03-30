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
    resident_list, resident_create, resident_detail, resident_edit, resident_delete,
    user_list, user_create, user_edit, user_delete, user_toggle_active,
    search_residents, search_complaints, search_visitors,
    
    # Admin - Staff Management
    staff_list, staff_create, staff_detail, staff_edit, staff_delete,
    
    # Admin - Property Management
    unit_list, unit_create, unit_edit, unit_delete,
    building_list, building_create, building_edit,
    
    # Admin - Billing
    bill_list, bill_create, bill_edit, bill_delete, bill_payment_history,
    
    # Admin - Complain Management
    complaint_list, complaint_detail, complaint_assign, complaint_close, complaint_update,
    
    # Admin - Notice Management
    notice_list, notice_create, notice_edit, notice_delete,
    
    # Admin - Amenities
    amenity_list, amenity_create, amenity_edit,
    amenity_booking_list, amenity_booking_approve,
    
    # Admin - Visitor Management
    visitor_list, visitor_approval_action, reports_dashboard, export_report_data,
    
    # Resident Features
    resident_bills_view, resident_payment_view, resident_bill_pdf_download,
    resident_stripe_checkout, resident_stripe_success, resident_demo_online_checkout,
    resident_complaint_list, resident_complaint_create, resident_complaint_detail,
    resident_amenities_view, resident_amenity_book, resident_booking_list, resident_booking_cancel,
    resident_notice_list, resident_notice_detail,
    resident_visitor_approval, resident_visitor_list,
    resident_profile_view, resident_profile_edit, resident_transactions,
    
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
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard_login_redirect'),
    path('resident-dashboard/', resident_dashboard, name='resident_dashboard_login_redirect'),
    path('staff-dashboard/', staff_dashboard, name='staff_dashboard_login_redirect'),
    path('management/dashboard/', admin_dashboard, name='admin_dashboard'),
    path('resident/dashboard/', resident_dashboard, name='resident_dashboard'),
    path('staff/dashboard/', staff_dashboard, name='staff_dashboard'),
    
    # ============= ADMIN URLS =============

    # Search
    path('management/search/residents/', search_residents, name='search_residents'),
    path('management/search/complaints/', search_complaints, name='search_complaints'),
    path('management/search/visitors/', search_visitors, name='search_visitors'),

    # User Management
    path('management/users/', user_list, name='user_list'),
    path('management/users/create/', user_create, name='user_create'),
    path('management/users/<int:user_id>/edit/', user_edit, name='user_edit'),
    path('management/users/<int:user_id>/delete/', user_delete, name='user_delete'),
    path('management/users/<int:user_id>/toggle-active/', user_toggle_active, name='user_toggle_active'),
    
    # Resident Management
    path('management/residents/', resident_list, name='resident_list'),
    path('management/residents/create/', resident_create, name='resident_create'),
    path('management/residents/<int:resident_id>/', resident_detail,  name='resident_detail'),
    path('management/residents/<int:resident_id>/edit/', resident_edit, name='resident_edit'),
    path('management/residents/<int:resident_id>/delete/', resident_delete, name='resident_delete'),
    
    # Staff Management
    path('management/staff/', staff_list, name='staff_list'),
    path('management/staff/create/', staff_create, name='staff_create'),
    path('management/staff/<int:staff_id>/', staff_detail, name='staff_detail'),
    path('management/staff/<int:staff_id>/edit/', staff_edit, name='staff_edit'),
    path('management/staff/<int:staff_id>/delete/', staff_delete, name='staff_delete'),
    
    # Unit/Property Management
    path('management/units/', unit_list, name='unit_list'),
    path('management/units/create/', unit_create, name='unit_create'),
    path('management/units/<int:unit_id>/edit/', unit_edit, name='unit_edit'),
    path('management/units/<int:unit_id>/delete/', unit_delete, name='unit_delete'),
    
    # Building Management
    path('management/buildings/', building_list, name='building_list'),
    path('management/buildings/create/', building_create, name='building_create'),
    path('management/buildings/<int:building_id>/edit/', building_edit, name='building_edit'),
    
    # Maintenance Billing
    path('management/bills/', bill_list, name='bill_list'),
    path('management/bills/create/', bill_create, name='bill_create'),
    path('management/bills/<int:bill_id>/edit/', bill_edit, name='bill_edit'),
    path('management/bills/<int:bill_id>/delete/', bill_delete, name='bill_delete'),
    path('management/bills/payment-history/', bill_payment_history, name='bill_payment_history'),
    
    # Complaint Management
    path('management/complaints/', complaint_list, name='complaint_list'),
    path('management/complaints/<int:complaint_id>/', complaint_detail, name='complaint_detail'),
    path('management/complaints/<int:complaint_id>/update/', complaint_update, name='complaint_update'),
    path('management/complaints/<int:complaint_id>/assign/', complaint_assign, name='complaint_assign'),
    path('management/complaints/<int:complaint_id>/close/', complaint_close, name='complaint_close'),
    
    # Notice Management
    path('management/notices/', notice_list, name='notice_list'),
    path('management/notices/create/', notice_create, name='notice_create'),
    path('management/notices/<int:notice_id>/edit/', notice_edit, name='notice_edit'),
    path('management/notices/<int:notice_id>/delete/', notice_delete, name='notice_delete'),
    
    # Amenities Management
    path('management/amenities/', amenity_list, name='amenity_list'),
    path('management/amenities/create/', amenity_create, name='amenity_create'),
    path('management/amenities/<int:amenity_id>/edit/', amenity_edit, name='amenity_edit'),
    path('management/amenities/bookings/', amenity_booking_list, name='amenity_booking_list'),
    path('management/amenities/bookings/<int:booking_id>/approve/', amenity_booking_approve, name='amenity_booking_approve'),
    
    # Visitor Management
    path('management/visitors/', visitor_list, name='visitor_list'),
    path('management/visitors/<int:visitor_id>/approval/', visitor_approval_action, name='visitor_approval_action'),
    path('management/reports/', reports_dashboard, name='reports_dashboard'),
    path('management/reports/export/', export_report_data, name='export_report_data'),
    
    # ============= RESIDENT URLS =============
    
    # Profile
    path('resident/profile/', resident_profile_view, name='resident_profile'),
    path('resident/profile/edit/', resident_profile_edit, name='resident_profile_edit'),
    
    # Bills & Payments
    path('resident/bills/', resident_bills_view, name='resident_bills'),
    path('resident/bills/<int:bill_id>/pay/', resident_payment_view, name='resident_payment'),
    path('resident/bills/<int:bill_id>/stripe/checkout/', resident_stripe_checkout, name='resident_stripe_checkout'),
    path('resident/bills/<int:bill_id>/stripe/success/', resident_stripe_success, name='resident_stripe_success'),
    path('resident/bills/<int:bill_id>/online/demo/', resident_demo_online_checkout, name='resident_demo_online_checkout'),
    path('resident/bills/<int:bill_id>/pdf/', resident_bill_pdf_download, name='resident_bill_pdf_download'),
    
    # Complaints
    path('resident/complaints/', resident_complaint_list, name='resident_complaints'),
    path('resident/complaints/create/', resident_complaint_create, name='resident_complaint_create'),
    path('resident/complaints/<int:complaint_id>/', resident_complaint_detail, name='resident_complaint_detail'),
    
    # Amenities
    path('resident/amenities/', resident_amenities_view, name='resident_amenities'),
    path('resident/amenities/<int:amenity_id>/book/', resident_amenity_book, name='resident_amenity_book'),
    path('resident/bookings/', resident_booking_list, name='resident_bookings'),
    path('resident/bookings/<int:booking_id>/cancel/', resident_booking_cancel, name='resident_booking_cancel'),
    
    # Notices
    path('resident/notices/', resident_notice_list, name='resident_notices'),
    path('resident/notices/<int:notice_id>/', resident_notice_detail, name='resident_notice_detail'),
    path('resident/transactions/', resident_transactions, name='resident_transactions'),
    
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
