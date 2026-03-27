from .models import Notification


def notification_badge(request):
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        has_resident_profile = request.user.role == 'RESIDENT' and hasattr(request.user, 'resident_profile')
        has_staff_profile = request.user.role == 'STAFF' and hasattr(request.user, 'staff_profile')
    else:
        unread_count = 0
        has_resident_profile = False
        has_staff_profile = False
    return {
        'notification_unread_count': unread_count,
        'has_resident_profile': has_resident_profile,
        'has_staff_profile': has_staff_profile,
    }
