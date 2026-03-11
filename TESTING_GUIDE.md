# 🧪 ROLE-BASED ACCESS CONTROL - TESTING GUIDE

## Quick Test Commands

### 1. Create Test Users for Each Role

```bash
python manage.py shell
```

```python
from django.contrib.auth import authenticate
from core.models import User
from socity.models import Resident, Staff, Unit

# Create ADMIN user
admin_user = User.objects.create_user(
    username='admin_test',
    email='admin@test.com',
    password='Admin@123',
    role='ADMIN',
    first_name='Admin',
    last_name='User'
)
print(f"✅ Admin created: {admin_user.username}")

# Create unit
unit, _ = Unit.objects.get_or_create(
    unit_no='101',
    defaults={'wing': 'A', 'floor': 1, 'unit_type': 'FLAT', 'sq_ft': 1000}
)

# Create RESIDENT user
resident_user = User.objects.create_user(
    username='resident_test',
    email='resident@test.com',
    password='Resident@123',
    role='RESIDENT',
    first_name='Resident',
    last_name='User'
)
resident = Resident.objects.create(
    user=resident_user,
    unit=unit,
    status='OWNER',
    member_count=3
)
print(f"✅ Resident created: {resident_user.username}")

# Create STAFF user
staff_user = User.objects.create_user(
    username='staff_test',
    email='staff@test.com',
    password='Staff@123',
    role='STAFF',
    first_name='Staff',
    last_name='User'
)
staff = Staff.objects.create(
    user=staff_user,
    designation='SECURITY',
    status='ACTIVE'
)
print(f"✅ Staff created: {staff_user.username}")

# Create VISITOR user
visitor_user = User.objects.create_user(
    username='visitor_test',
    email='visitor@test.com',
    password='Visitor@123',
    role='VISITOR',
    first_name='Visitor',
    last_name='User'
)
print(f"✅ Visitor created: {visitor_user.username}")

print("\n✅ All test users created!")
```

### 2. Test Authentication

```python
from django.contrib.auth import authenticate

# Test each user can login
users = [
    ('admin_test', 'Admin@123'),
    ('admin@test.com', 'Admin@123'),
    ('resident_test', 'Resident@123'),
    ('staff_test', 'Staff@123'),
    ('visitor_test', 'Visitor@123'),
]

for username, password in users:
    user = authenticate(username=username, password=password)
    if user:
        print(f"✅ {username} → {user.get_role_display()}")
    else:
        print(f"❌ {username} → Failed")
```

---

## Browser Testing

### Test 1: Admin Access

```
Login: admin_test / Admin@123

✅ Can access:
- /dashboard/ → Admin dashboard
- /admin/residents/ → Resident list
- /admin/bills/ → Bill management
- /admin/complaints/ → Complaint management
- /admin/notices/ → Notice management
- /admin/amenities/ → Amenity management
- /admin/visitors/ → Visitor logs
- /admin/ → Django admin panel

❌ Cannot access (→ 403):
- /resident/bills/
- /resident/complaints/
- /staff/tasks/
- /staff/visitors/

Navbar shows: Residents, Bills, Complaints, Notices, Admin Panel
```

### Test 2: Resident Access

```
Login: resident_test / Resident@123

✅ Can access:
- /dashboard/ → Resident dashboard
- /resident/profile/ → My profile
- /resident/bills/ → Maintenance bills
- /resident/complaints/ → My complaints
- /resident/amenities/ → Book amenities
- /resident/bookings/ → My bookings
- /resident/notices/ → Society notices
- /resident/visitor-log/ → Visitor log

❌ Cannot access (→ 403):
- /admin/residents/
- /admin/bills/
- /staff/tasks/
- /staff/complaints/

Navbar shows: Dashboard, Profile, Bills, Complaints, Notices
```

### Test 3: Staff Access

```
Login: staff_test / Staff@123

✅ Can access:
- /dashboard/ → Staff dashboard
- /staff/tasks/ → Assigned tasks
- /staff/complaints/ → Assigned complaints
- /staff/visitors/ → Visitor management
- /staff/visitors/entry/ → Register entry

❌ Cannot access (→ 403):
- /admin/residents/
- /admin/bills/
- /resident/bills/
- /resident/complaints/

Navbar shows: Dashboard, Tasks, Complaints, Visitors
```

### Test 4: Visitor Access

```
Login: visitor_test / Visitor@123

✅ Can access:
- /dashboard/ → Visitor dashboard (limited)
- /visitor/register/ → Register visit
- /resident/notices/ → Society notices

❌ Cannot access (→ 403):
- /admin/residents/
- /resident/bills/
- /resident/complaints/
- /staff/tasks/

Navbar shows: Dashboard, Notices, Profile, Logout

Dashboard shows: "Only Visitor Features" message
```

### Test 5: Manual URL Entry

```
Without Login:
- /admin/residents/ → Redirect to /login/
- /resident/bills/ → Redirect to /login/

As Visitor trying Admin routes:
- /admin/residents/ → Redirect to /login/, message "Only administrators..."
- /admin/bills/ → Same

As Resident trying Staff routes:
- /staff/tasks/ → 403 Forbidden Page
- /staff/complaints/ → 403 Forbidden Page

As Admin trying Resident routes:
- /resident/complaints/ → 403 Forbidden Page
```

---

## Advanced Testing

### Test Case-Insensitive Login

```bash
python manage.py shell
```

```python
from django.contrib.auth import authenticate

# Should work - case variations
tests = [
    ('admin_test', 'Admin@123'),           # username exact
    ('ADMIN_TEST', 'Admin@123'),           # username UPPER
    ('Admin_Test', 'Admin@123'),           # username mixed
    ('admin@test.com', 'Admin@123'),       # email exact
    ('ADMIN@TEST.COM', 'Admin@123'),       # email UPPER
    ('Admin@Test.Com', 'Admin@123'),       # email mixed
    ('  admin_test  ', 'Admin@123'),       # username with spaces (trimmed)
]

for username, password in tests:
    user = authenticate(username=username, password=password)
    status = "✅" if user else "❌"
    print(f"{status} {username}")
```

---

## Error Testing

### 403 Forbidden Page

Requirements:
- ✅ Shows "Access Denied" message
- ✅ Shows user's current role
- ✅ Shows what they can do (role-specific)
- ✅ Provides "Back to Dashboard" button
- ✅ Provides "Go to Home" button
- ✅ Status code = 403

### Wrong Password

Requirements:
- ✅ Shows "Invalid username or password"
- ✅ Stays on /login/ page
- ✅ Form data cleared
- ✅ No console errors

### Non-Existent Email

Requirements:
- ✅ Shows "Invalid username or password"
- ✅ No stack trace visible
- ✅ No database errors

---

## Performance Testing

```python
from django.test import Client
from django.contrib.auth import authenticate
import time

client = Client()

# Login times
users = [
    ('admin_test', 'Admin@123'),
    ('resident_test', 'Resident@123'),
    ('staff_test', 'Staff@123'),
    ('visitor_test', 'Visitor@123'),
]

for username, password in users:
    start = time.time()
    response = client.post('/login/', {'username': username, 'password': password})
    elapsed = time.time() - start
    status = "Fast" if elapsed < 0.1 else "Normal"
    print(f"{username}: {elapsed:.3f}s ({status})")
```

---

## Final Verification Checklist

- [ ] All 4 user roles created successfully
- [ ] Each role can login with username and email
- [ ] Login case-insensitive (uppercase, lowercase, mixed)
- [ ] Login works with spaces in input
- [ ] Admin sees all admin features only
- [ ] Resident sees all resident features only
- [ ] Staff sees all staff features only
- [ ] Visitor sees limited features only
- [ ] Manual URL entry to restricted pages → 403
- [ ] 403 page shows meaningful error message
- [ ] Navbar changes based on role
- [ ] Dashboard content changes based on role
- [ ] Logout works for all roles
- [ ] Re-login possible after logout
- [ ] Session expires properly
- [ ] No cross-role data leakage visible
- [ ] Performance acceptable (< 100ms per request)

---

## Production Deployment

Before deploying to production:

```python
# settings.py
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']
SECRET_KEY = os.getenv('SECRET_KEY')  # Use environment variable

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create backup
python manage.py dumpdata > backup.json
```

---

## Troubleshooting

**Issue:** "Invalid username or password" with correct credentials
- ✅ Already Fixed: Updated backends.py with case-insensitive lookup and trim
- Check: User is_active = True
- Check: Password matches (not from old backup)

**Issue:** 403 page not showing
- Check: error_403 handler added to urls.py
- Check: 403.html exists in templates/

**Issue:** Navbar not changing by role
- Check: user.role is set correctly
- Check: Template has {% if user.role == 'ROLE' %} conditions
- Check: Browser cache cleared (Ctrl+F5)

**Issue:** Decorator not blocking access
- Check: @decorator placed before view function
- Check: User has correct role in database
- Check: Related profile (Resident/Staff) exists if using resident_required/@staff_required

