from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

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
