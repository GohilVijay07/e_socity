from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailOrUsernameAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login with either email or username
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        identifier = str(username).strip()
        if not identifier:
            return None
        
        try:
            # Try to find user by email or username
            user = User.objects.get(Q(email__iexact=identifier) | Q(username__iexact=identifier))
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # If multiple users are returned, try to get by email first
            user = User.objects.filter(Q(email__iexact=identifier) | Q(username__iexact=identifier)).first()
        
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
