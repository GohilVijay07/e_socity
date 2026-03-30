from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Count

from .models import Notification


def create_notification(user, title, message, notification_type='INFO', action_url='', send_email=False, email_subject='Notification'):
    """Create an in-app notification and optionally send email."""
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        action_url=action_url or '',
    )

    if send_email and user.email:
        try:
            send_mail(
                subject=email_subject,
                message=f"{title}\n\n{message}",
                from_email=getattr(settings, 'EMAIL_HOST_USER', ''),
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

    return notification


def send_email_verification(user, request):
    """Generate verification token and send verification email."""
    from .models import EmailVerificationToken

    token = EmailVerificationToken.create_for_user(user)
    verify_link = request.build_absolute_uri(f"/core/email-verify/{token.token}/")
    subject = 'Verify your e-Socity account email'
    message = (
        f"Hello {user.get_full_name() or user.username},\n\n"
        f"Please verify your email by visiting this link:\n{verify_link}\n\n"
        "This link expires in 24 hours."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, 'EMAIL_HOST_USER', ''),
        recipient_list=[user.email],
        fail_silently=False,
    )

    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=['email_verification_sent_at'])
    return token


def ensure_user_role_setup(user):
    """Auto-provision role-specific profile records for new users.

    Returns a dict with details about created entities.
    """
    from socity.models import Resident, Staff, Unit

    result = {
        'resident_created': False,
        'staff_created': False,
        'unit_assigned': None,
        'unit_auto_created': False,
    }

    if user.role == 'RESIDENT':
        if not Resident.objects.filter(user=user).exists():
            unit = (
                Unit.objects.annotate(resident_count=Count('residents'))
                .filter(resident_count=0)
                .order_by('wing', 'unit_no')
                .first()
            )

            if unit is None:
                unit = (
                    Unit.objects.annotate(resident_count=Count('residents'))
                    .order_by('resident_count', 'wing', 'unit_no')
                    .first()
                )

            if unit is None:
                # Fallback: create an auto unit so resident onboarding never blocks.
                idx = 1
                while True:
                    unit_no = f"AUTO{idx:03d}"
                    if not Unit.objects.filter(unit_no=unit_no).exists():
                        break
                    idx += 1

                unit = Unit.objects.create(
                    unit_no=unit_no,
                    wing='AUTO',
                    floor=0,
                    unit_type='1BHK',
                    sq_ft=500,
                    is_occupied=True,
                )
                result['unit_auto_created'] = True

            Resident.objects.create(
                user=user,
                unit=unit,
                status='TENANT',
                vehicle_no='',
                member_count=1,
                move_in_date=timezone.now().date(),
                emergency_contact='',
                emergency_phone='',
                occupation='',
            )

            if not unit.is_occupied:
                unit.is_occupied = True
                unit.save(update_fields=['is_occupied'])

            result['resident_created'] = True
            result['unit_assigned'] = str(unit)

    elif user.role == 'STAFF':
        if not Staff.objects.filter(user=user).exists():
            Staff.objects.create(
                user=user,
                designation='OTHER',
                department='General Operations',
                status='ACTIVE',
                join_date=timezone.now().date(),
                emergency_contact='',
                emergency_phone='',
                address='',
            )
            result['staff_created'] = True

    return result
