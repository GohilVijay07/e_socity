from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User
from socity.models import (
    Unit, Resident, MaintenanceBill, Visitor, 
    Complaint, Amenity, AmenityBooking, Notice, Transaction
)

# Customize Admin Site Headers
admin.site.site_header = "eSociety Management System"
admin.site.site_title = "eSociety Admin"
admin.site.index_title = "Welcome to eSociety Administration"


# 1. Custom User Admin
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'get_full_name', 'role', 'phone', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'profile_image', 'date_of_birth', 'is_active_resident')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'email', 'first_name', 'last_name')}),
    )


# 2. Unit Admin
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['unit_no', 'wing', 'floor', 'unit_type', 'sq_ft', 'is_occupied', 'occupancy_status', 'created_at']
    list_filter = ['wing', 'floor', 'unit_type', 'is_occupied']
    search_fields = ['unit_no', 'wing']
    list_editable = ['is_occupied']
    ordering = ['wing', 'floor', 'unit_no']
    
    def occupancy_status(self, obj):
        if obj.is_occupied:
            return format_html('<span style="color: green; font-weight: bold;">●</span> Occupied')
        return format_html('<span style="color: red; font-weight: bold;">●</span> Vacant')
    occupancy_status.short_description = 'Status'


# 3. Resident Admin
@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ['get_name', 'unit', 'status', 'vehicle_no', 'member_count', 'move_in_date', 'emergency_contact']
    list_filter = ['status', 'move_in_date', 'unit__wing']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'unit__unit_no', 'vehicle_no']
    date_hierarchy = 'move_in_date'
    autocomplete_fields = ['user', 'unit']
    
    def get_name(self, obj):
        return obj.user.get_full_name()
    get_name.short_description = 'Resident Name'


# 4. Maintenance Bill Admin
@admin.register(MaintenanceBill)
class MaintenanceBillAdmin(admin.ModelAdmin):
    list_display = ['unit', 'billing_month', 'amount', 'penalty', 'total_amount', 'status', 'status_badge', 'payment_date']
    list_filter = ['status', 'billing_month', 'unit__wing']
    search_fields = ['unit__unit_no', 'unit__wing']
    date_hierarchy = 'billing_month'
    list_editable = ['status']
    actions = ['mark_as_paid', 'mark_as_overdue']
    
    def total_amount(self, obj):
        return obj.amount + obj.penalty
    total_amount.short_description = 'Total Amount'
    
    def status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'PAID': 'green',
            'OVERDUE': 'red',
            'PARTIAL': 'blue',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='PAID', payment_date=timezone.now())
        self.message_user(request, f'{updated} bill(s) marked as paid.')
    mark_as_paid.short_description = 'Mark selected bills as Paid'
    
    def mark_as_overdue(self, request, queryset):
        updated = queryset.update(status='OVERDUE')
        self.message_user(request, f'{updated} bill(s) marked as overdue.')
    mark_as_overdue.short_description = 'Mark selected bills as Overdue'


# 5. Visitor Admin
@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'visit_unit', 'host_name', 'purpose', 'status_badge', 'in_time', 'out_time']
    list_filter = ['status', 'in_time', 'visit_unit__wing']
    search_fields = ['name', 'phone', 'visit_unit__unit_no', 'vehicle_no']
    date_hierarchy = 'in_time'
    autocomplete_fields = ['visit_unit', 'host']
    
    def host_name(self, obj):
        return obj.host.user.get_full_name() if obj.host else '-'
    host_name.short_description = 'Host'
    
    def status_badge(self, obj):
        color = 'green' if obj.status == 'IN' else 'gray'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# 6. Complaint Admin
@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['title', 'raised_by_name', 'category', 'priority_badge', 'status', 'status_badge', 'assigned_to', 'created_at']
    list_filter = ['status', 'category', 'priority', 'created_at']
    search_fields = ['title', 'description', 'raised_by__user__first_name', 'raised_by__user__last_name']
    date_hierarchy = 'created_at'
    list_editable = ['status']
    autocomplete_fields = ['raised_by', 'assigned_to']
    actions = ['mark_as_resolved', 'mark_as_in_progress']
    
    def raised_by_name(self, obj):
        return obj.raised_by.user.get_full_name()
    raised_by_name.short_description = 'Raised By'
    
    def priority_badge(self, obj):
        colors = {1: 'green', 2: 'orange', 3: 'red'}
        labels = {1: 'Low', 2: 'Medium', 3: 'High'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">{}</span>',
            colors.get(obj.priority, 'gray'),
            labels.get(obj.priority, 'Unknown')
        )
    priority_badge.short_description = 'Priority'
    
    def status_badge(self, obj):
        colors = {
            'OPEN': 'red',
            'IN_PROGRESS': 'orange',
            'RESOLVED': 'green',
            'CLOSED': 'gray',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='RESOLVED', resolved_date=timezone.now())
        self.message_user(request, f'{updated} complaint(s) marked as resolved.')
    mark_as_resolved.short_description = 'Mark selected complaints as Resolved'
    
    def mark_as_in_progress(self, request, queryset):
        updated = queryset.update(status='IN_PROGRESS')
        self.message_user(request, f'{updated} complaint(s) marked as in progress.')
    mark_as_in_progress.short_description = 'Mark selected complaints as In Progress'


# 7. Amenity Admin
@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_available', 'availability_status', 'created_at']
    list_filter = ['is_available']
    search_fields = ['name', 'description']
    list_editable = ['is_available']
    
    def availability_status(self, obj):
        if obj.is_available:
            return format_html('<span style="color: green; font-weight: bold;">✓ Available</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Not Available</span>')
    availability_status.short_description = 'Status'


# 8. Amenity Booking Admin
@admin.register(AmenityBooking)
class AmenityBookingAdmin(admin.ModelAdmin):
    list_display = ['resident_name', 'amenity', 'booking_date', 'start_time', 'end_time', 'status', 'status_badge', 'purpose']
    list_filter = ['status', 'booking_date', 'amenity']
    search_fields = ['resident__user__first_name', 'resident__user__last_name', 'amenity__name', 'purpose']
    date_hierarchy = 'booking_date'
    list_editable = ['status']
    autocomplete_fields = ['resident', 'amenity']
    actions = ['confirm_bookings', 'cancel_bookings', 'mark_completed']
    
    def resident_name(self, obj):
        return obj.resident.user.get_full_name()
    resident_name.short_description = 'Resident'
    
    def status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'CONFIRMED': 'green',
            'CANCELLED': 'red',
            'COMPLETED': 'gray',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def confirm_bookings(self, request, queryset):
        updated = queryset.update(status='CONFIRMED')
        self.message_user(request, f'{updated} booking(s) confirmed.')
    confirm_bookings.short_description = 'Confirm selected bookings'
    
    def cancel_bookings(self, request, queryset):
        updated = queryset.update(status='CANCELLED')
        self.message_user(request, f'{updated} booking(s) cancelled.')
    cancel_bookings.short_description = 'Cancel selected bookings'
    
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='COMPLETED')
        self.message_user(request, f'{updated} booking(s) marked as completed.')
    mark_completed.short_description = 'Mark selected bookings as Completed'


# 9. Notice Admin
@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority_badge', 'posted_by', 'posted_date', 'expiry_date', 'is_active', 'active_status']
    list_filter = ['priority', 'is_active', 'posted_date']
    search_fields = ['title', 'content']
    date_hierarchy = 'posted_date'
    list_editable = ['is_active']
    autocomplete_fields = ['posted_by']
    
    def priority_badge(self, obj):
        colors = {
            'LOW': 'green',
            'MEDIUM': 'blue',
            'HIGH': 'orange',
            'URGENT': 'red',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">{}</span>',
            colors.get(obj.priority, 'gray'),
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def active_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ Active</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Inactive</span>')
    active_status.short_description = 'Status'


# 10. Transaction Admin
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['reference_no', 'resident_name', 'transaction_type', 'amount', 'payment_mode', 'transaction_date']
    list_filter = ['transaction_type', 'payment_mode', 'transaction_date']
    search_fields = ['reference_no', 'resident__user__first_name', 'resident__user__last_name', 'remarks']
    date_hierarchy = 'transaction_date'
    autocomplete_fields = ['resident', 'bill']
    readonly_fields = ['transaction_date']
    
    def resident_name(self, obj):
        return obj.resident.user.get_full_name()
    resident_name.short_description = 'Resident'