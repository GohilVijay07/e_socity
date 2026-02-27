# eSociety App Structure Documentation

## Overview
Project ko do apps mein divide kiya gaya hai:
- **core**: Authentication, User Management, Admin Interface
- **socity**: Business Logic, Models, Views, Forms

## App Architecture

### CORE App (Authentication & Admin)
**Models:**
- `User` - Custom user model with role-based access

**Admin Access:**
- Core admin can manage all models from both apps
- All society models (Unit, Resident, Bills, Complaints, etc.) are registered in core admin

**Views:**
- `home()` - Home page
- `dashboard()` - User dashboard
- `userSignupView()` - User registration
- `userLoginView()` - User login
- `userLogoutView()` - User logout

**Forms:**
- `UserSignupForm` - User registration
- `UserLoginForm` - User login
- `UserProfileForm` - Profile editing

### SOCITY App (Business Logic)
**Models:**
- `Unit` - Property/flat details
- `Resident` - Resident profile linked to User
- `MaintenanceBill` - Monthly maintenance bills
- `Visitor` - Visitor tracking
- `Complaint` - Issue/complaint management
- `Amenity` - Society amenities/facilities
- `AmenityBooking` - Amenity reservations
- `Notice` - Society notices and announcements
- `Transaction` - Payment transaction records

**Views:**
- `profile_view()` - User profile view
- `profile_edit()` - Profile editing
- `bills_view()` - Maintenance bills
- `complaints_view()` - Complaint listing
- `complaint_create()` - Create new complaint
- `complaint_detail()` - Complaint details
- `amenities_view()` - Available amenities
- `amenity_book()` - Book amenity
- `bookings_view()` - User's bookings
- `notices_view()` - Society notices
- `notice_detail()` - Notice details
- `transactions_view()` - Payment history
- `visitors_view()` - Visitor log

**Forms:**
- `ComplaintForm` - Complaint creation
- `AmenityBookingForm` - Amenity booking

## Database Structure

### Core Models
```
User (Custom Auth Model)
├── role (ADMIN, RESIDENT, VISITOR, STAFF)
├── phone
├── profile_image
├── date_of_birth
└── is_active_resident
```

### Socity Models
```
Unit
├── unit_no (unique)
├── wing
├── floor
├── unit_type
├── sq_ft
└── is_occupied

Resident (OneToOne with User)
├── user (FK)
├── unit (FK)
├── status (OWNER, TENANT, FAMILY_MEMBER)
├── vehicle_no
├── member_count
├── move_in_date
└── emergency_contact

MaintenanceBill
├── unit (FK)
├── billing_month
├── amount
├── penalty
└── status (PENDING, PAID, OVERDUE)

Complaint
├── raised_by (FK to Resident)
├── category
├── title
├── description
├── status
├── priority
└── assigned_to (FK to User)

Visitor
├── name
├── phone
├── visit_unit (FK to Unit)
├── host (FK to Resident, nullable)
├── purpose
└── status (IN, OUT)

Amenity
├── name
├── description
├── is_available
└── image

AmenityBooking
├── resident (FK)
├── amenity (FK)
├── booking_date
├── start_time
├── end_time
├── status
└── purpose

Notice
├── title
├── content
├── priority
├── posted_by (FK to User)
├── posted_date
├── expiry_date
└── is_active

Transaction
├── bill (FK, nullable)
├── resident (FK)
├── amount
├── transaction_type
├── payment_mode
├── reference_no
└── transaction_date
```

## URL Structure

### Authentication URLs
- `/` - Home
- `/signup/` - Register
- `/login/` - Login
- `/logout/` - Logout
- `/dashboard/` - Dashboard

### User Management URLs
- `/profile/` - View profile
- `/profile/edit/` - Edit profile

### Bills URLs
- `/bills/` - View bills

### Complaint URLs
- `/complaints/` - List complaints
- `/complaints/create/` - Create complaint
- `/complaints/<id>/` - Complaint details

### Amenity URLs
- `/amenities/` - List amenities
- `/amenities/book/` - Book amenity
- `/bookings/` - View bookings

### Notice URLs
- `/notices/` - List notices
- `/notices/<id>/` - Notice details

### Payment URLs
- `/transactions/` - Transaction history

### Visitor URLs
- `/visitors/` - Visitor log

## Settings

### INSTALLED_APPS
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',      # Authentication & Admin
    'socity',    # Business Logic
]
```

### Custom User Model
```python
AUTH_USER_MODEL = 'core.User'
```

## Admin Interface

Core admin panel provides centralized management for:

1. **Users** - Manage all users with roles (Admin, Resident, Visitor, Staff)
2. **Units** - Manage property/flat details
3. **Residents** - Link residents to units and users
4. **Bills** - Create and manage maintenance bills
5. **Complaints** - Manage complaint tracking
6. **Visitors** - Track visitor log
7. **Amenities** - Manage society facilities
8. **Bookings** - Manage amenity reservations
9. **Notices** - Post announcements
10. **Transactions** - Track payments

## Usage Guidelines

### For Admins:
1. Go to `/admin/` to manage all society operations
2. Create users with appropriate roles
3. Manage units, residents, and billing
4. Review complaints and resolve issues
5. Post notices and announcements

### For Residents:
1. Sign up and create account
2. View and edit profile
3. Check maintenance bills
4. File complaints
5. Book amenities
6. View notices
7. Check payment history
8. Track visitors

## Security Features

- Custom User model with role-based access control
- User authentication required for most views
- One-to-one relationship between User and Resident
- Secure admin interface for management

## Future Enhancements

- Payment gateway integration
- Email notifications
- SMS alerts
- Advanced reporting
- Mobile app
- API endpoints
