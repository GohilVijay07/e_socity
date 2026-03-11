"""
TEMPLATE CREATION GUIDE FOR E-SOCIETY MANAGEMENT SYSTEM

This file provides template structure examples for all required templates.
Use these as starting points and customize with your design/styling.

Location: templates/socity/
"""

# ============================================================================
# BASE TEMPLATE STRUCTURE (templates/base.html)
# ============================================================================

TEMPLATE_BASE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}e-Society Management{% endblock %}</title>
    {% load static %}
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{% static 'css/style.css' %}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{% url 'home' %}">🏘️ e-Society</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    {% if user.is_authenticated %}
                        {% if user.role == 'ADMIN' %}
                            <li class="nav-item"><a class="nav-link" href="{% url 'admin_dashboard' %}">Dashboard</a></li>
                            <li class="nav-item"><a class="nav-link" href="{% url 'resident_list' %}">Residents</a></li>
                            <li class="nav-item"><a class="nav-link" href="{% url 'staff_list' %}">Staff</a></li>
                            <li class="nav-item"><a class="nav-link" href="{% url 'bill_list' %}">Bills</a></li>
                            <li class="nav-item"><a class="nav-link" href="{% url 'complaint_list' %}">Complaints</a></li>
                        {% elif user.role == 'RESIDENT' %}
                            <li class="nav-item"><a class="nav-link" href="{% url 'resident_dashboard' %}">Dashboard</a></li>
                            <li class="nav-item"><a class="nav-link" href="{% url 'resident_bills' %}">Bills</a></li>
                            <li class="nav-item"><a class="nav-link" href="{% url 'resident_complaints' %}">Complaints</a></li>
                            <li class="nav-item"><a class="nav-link" href="{% url 'resident_amenities' %}">Amenities</a></li>
                        {% elif user.role == 'STAFF' %}
                            <li class="nav-item"><a class="nav-link" href="{% url 'staff_dashboard' %}">Dashboard</a></li>
                            <li class="nav-item"><a class="nav-link" href="{% url 'staff_tasks' %}">Tasks</a></li>
                            <li class="nav-item"><a class="nav-link" href="{% url 'staff_visitors' %}">Visitors</a></li>
                        {% endif %}
                        <li class="nav-item"><a class="nav-link" href="{% url 'resident_profile' %}">Profile</a></li>
                        <li class="nav-item"><a class="nav-link" href="{% url 'logout' %}">Logout</a></li>
                    {% else %}
                        <li class="nav-item"><a class="nav-link" href="{% url 'login' %}">Login</a></li>
                        <li class="nav-item"><a class="nav-link" href="{% url 'signup' %}">Sign Up</a></li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <main class="py-4">
        <div class="container">
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
            
            {% block content %}{% endblock %}
        </div>
    </main>

    <footer class="bg-dark text-white mt-5 py-4">
        <div class="container text-center">
            <p>&copy; 2026 e-Society Management System. All rights reserved.</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
'''


# ============================================================================
# ADMIN DASHBOARD TEMPLATE EXAMPLE
# ============================================================================

ADMIN_DASHBOARD = '''
{% extends 'base.html' %}

{% block title %}Admin Dashboard - e-Society{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col-md-12">
        <h1 class="mb-4">📊 Admin Dashboard</h1>
    </div>
</div>

<!-- Statistics Cards Row 1 -->
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card bg-primary text-white">
            <div class="card-body">
                <h5 class="card-title">Total Residents</h5>
                <p class="card-text display-4">{{ total_residents }}</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-success text-white">
            <div class="card-body">
                <h5 class="card-title">Staff Members</h5>
                <p class="card-text display-4">{{ total_staff }}</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-info text-white">
            <div class="card-body">
                <h5 class="card-title">Total Units</h5>
                <p class="card-text display-4">{{ total_units }}</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-warning text-dark">
            <div class="card-body">
                <h5 class="card-title">Occupied Units</h5>
                <p class="card-text display-4">{{ occupied_units }}</p>
            </div>
        </div>
    </div>
</div>

<!-- Complaints & Billing Cards -->
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card bg-danger text-white">
            <div class="card-body">
                <h5 class="card-title">Open Complaints</h5>
                <p class="card-text display-4">{{ open_complaints }}</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-danger text-white">
            <div class="card-body">
                <h5 class="card-title">Pending Bills</h5>
                <p class="card-text display-4">{{ total_pending_bills }}</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-success text-white">
            <div class="card-body">
                <h5 class="card-title">Paid Bills</h5>
                <p class="card-text display-4">{{ total_paid_bills }}</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-info text-white">
            <div class="card-body">
                <h5 class="card-title">Today Visitors</h5>
                <p class="card-text display-4">{{ today_visitors }}</p>
            </div>
        </div>
    </div>
</div>

<!-- Unpaid Amount -->
<div class="row mb-4">
    <div class="col-md-12">
        <div class="card bg-warning text-dark">
            <div class="card-body">
                <h5 class="card-title">💰 Total Unpaid Amount</h5>
                <p class="card-text display-5">₹ {{ total_unpaid_amount }}</p>
            </div>
        </div>
    </div>
</div>

<!-- Recent Activities -->
<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h5>📋 Recent Complaints</h5>
            </div>
            <div class="card-body">
                {% for complaint in recent_complaints %}
                    <p>
                        <a href="{% url 'complaint_detail' complaint.id %}">{{ complaint.title }}</a>
                        <span class="badge bg-{{ complaint.status|lower }}">{{ complaint.get_status_display }}</span>
                    </p>
                {% endfor %}
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5>📢 Recent Notices</h5>
            </div>
            <div class="card-body">
                {% for notice in recent_notices %}
                    <p>
                        <strong>{{ notice.title }}</strong>
                        <br>
                        <small class="text-muted">{{ notice.posted_date|date:"M d, Y" }}</small>
                    </p>
                {% endfor %}
            </div>
        </div>
    </div>
</div>

<!-- Quick Actions -->
<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h5>Quick Actions</h5>
            </div>
            <div class="card-body">
                <a href="{% url 'resident_list' %}" class="btn btn-primary">Manage Residents</a>
                <a href="{% url 'staff_list' %}" class="btn btn-success">Manage Staff</a>
                <a href="{% url 'bill_list' %}" class="btn btn-warning">View Bills</a>
                <a href="{% url 'complaint_list' %}" class="btn btn-danger">View Complaints</a>
                <a href="{% url 'notice_list' %}" class="btn btn-info">Post Notice</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''


# ============================================================================
# LIST TEMPLATE EXAMPLE (resident_list.html)
# ============================================================================

RESIDENT_LIST = '''
{% extends 'base.html' %}

{% block title %}Residents - e-Society{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col-md-8">
        <h1>👥 Residents</h1>
    </div>
    <div class="col-md-4 text-end">
        <a href="{% url 'resident_create' %}" class="btn btn-success">+ Add Resident</a>
    </div>
</div>

<!-- Search & Filter -->
<div class="card mb-4">
    <div class="card-body">
        <form method="GET" class="row g-3">
            <div class="col-md-6">
                <input type="text" class="form-control" name="search" placeholder="Search name/email/unit..." value="{{ search_query }}">
            </div>
            <div class="col-md-3">
                <select class="form-select" name="status">
                    <option value="">All Status</option>
                    {% for value, label in status_choices %}
                        <option value="{{ value }}">{{ label }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-3">
                <button type="submit" class="btn btn-primary w-100">Search</button>
            </div>
        </form>
    </div>
</div>

<!-- Residents Table -->
<div class="card">
    <div class="table-responsive">
        <table class="table table-hover mb-0">
            <thead class="table-dark">
                <tr>
                    <th>Name</th>
                    <th>Unit</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>Status</th>
                    <th>Move-in Date</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for resident in residents %}
                <tr>
                    <td><strong>{{ resident.user.get_full_name }}</strong></td>
                    <td>{{ resident.unit.unit_no }}</td>
                    <td>{{ resident.user.email }}</td>
                    <td>{{ resident.user.phone }}</td>
                    <td><span class="badge bg-success">{{ resident.get_status_display }}</span></td>
                    <td>{{ resident.move_in_date|date:"M d, Y" }}</td>
                    <td>
                        <a href="{% url 'resident_detail' resident.id %}" class="btn btn-sm btn-info">View</a>
                        <a href="{% url 'resident_edit' resident.id %}" class="btn btn-sm btn-warning">Edit</a>
                        <a href="{% url 'resident_delete' resident.id %}" class="btn btn-sm btn-danger">Delete</a>
                    </td>
                </tr>
                {% empty %}
                <tr>
                    <td colspan="7" class="text-center py-4">No residents found</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
'''


# ============================================================================
# FORM TEMPLATE EXAMPLE (bill_form.html)
# ============================================================================

BILL_FORM = '''
{% extends 'base.html' %}
{% load crispy_forms_tags %}

{% block title %}{{ title }} - e-Society{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h4>{{ title }}</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    {% csrf_token %}
                    {{ form|crispy }}
                    <button type="submit" class="btn btn-primary">
                        {% if bill %}Update Bill{% else %}Create Bill{% endif %}
                    </button>
                    <a href="{% url 'bill_list' %}" class="btn btn-secondary">Cancel</a>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''


# ============================================================================
# RESIDENT DASHBOARD TEMPLATE EXAMPLE
# ============================================================================

RESIDENT_DASHBOARD = '''
{% extends 'base.html' %}

{% block title %}My Dashboard - e-Society{% endblock %}

{% block content %}
<h1 class="mb-4">👋 Welcome, {{ user.first_name }}!</h1>

<!-- Unit Info -->
<div class="row mb-4">
    <div class="col-md-12">
        <div class="card bg-light">
            <div class="card-body">
                <h5>🏠 Your Unit</h5>
                <p class="fs-5"><strong>{{ resident.unit.unit_no }}</strong> ({{ resident.unit.get_unit_type_display }})</p>
                <p>Wing: {{ resident.unit.wing }} | Floor: {{ resident.unit.floor }}</p>
            </div>
        </div>
    </div>
</div>

<!-- Quick Stats -->
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h6 class="text-muted">Pending Bills</h6>
                <p class="display-4">{{ pending_bills }}</p>
                <p class="text-danger"><strong>₹ {{ total_bill_amount }}</strong></p>
                <a href="{% url 'resident_bills' %}" class="btn btn-sm btn-warning">Pay Now</a>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h6 class="text-muted">My Complaints</h6>
                <p class="display-4">{{ open_complaints }}</p>
                <a href="{% url 'resident_complaints' %}" class="btn btn-sm btn-primary">View</a>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h6 class="text-muted">Pending Bookings</h6>
                <p class="display-4">{{ pending_bookings }}</p>
                <a href="{% url 'resident_bookings' %}" class="btn btn-sm btn-info">View</a>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h6 class="text-muted">Today Visitors</h6>
                <p class="display-4">{{ today_visitors }}</p>
                <a href="{% url 'resident_visitor_log' %}" class="btn btn-sm btn-success">View</a>
            </div>
        </div>
    </div>
</div>

<!-- Recent Notices -->
<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header bg-info text-white">
                <h5>📢 Recent Notices</h5>
            </div>
            <div class="card-body">
                {% for notice in notices %}
                    <div class="mb-3">
                        <h6>{{ notice.title }}</h6>
                        <small class="text-muted">{{ notice.posted_date|date:"M d, Y" }}</small>
                        <p class="text-truncate">{{ notice.content|truncatewords:20 }}</p>
                    </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <!-- Quick Actions -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5>⚡ Quick Actions</h5>
            </div>
            <div class="card-body">
                <div class="d-grid gap-2">
                    <a href="{% url 'resident_bills' %}" class="btn btn-outline-primary">💳 Pay Bills</a>
                    <a href="{% url 'resident_complaint_create' %}" class="btn btn-outline-danger">🆘 File Complaint</a>
                    <a href="{% url 'resident_amenity_book' %}" class="btn btn-outline-info">🎾 Book Amenity</a>
                    <a href="{% url 'resident_visitor_approvals' %}" class="btn btn-outline-success">✅ Approve Visitors</a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''


# ============================================================================
# TEMPLATE STRUCTURE SUMMARY
# ============================================================================

TEMPLATE_STRUCTURE = '''
templates/
├── base.html ← Main template with navbar & layout
├── socity/
│   ├── admin/
│   │   ├── admin_dashboard.html
│   │   ├── resident_list.html
│   │   ├── resident_detail.html
│   │   ├── resident_form.html
│   │   ├── staff_list.html
│   │   ├── staff_detail.html
│   │   ├── staff_form.html
│   │   ├── unit_list.html
│   │   ├── unit_form.html
│   │   ├── building_list.html
│   │   ├── building_form.html
│   │   ├── bill_list.html
│   │   ├── bill_form.html
│   │   ├── bill_payment_history.html
│   │   ├── complaint_list.html
│   │   ├── complaint_detail.html
│   │   ├── complaint_assign.html
│   │   ├── notice_list.html
│   │   ├── notice_form.html
│   │   ├── amenity_list.html
│   │   ├── amenity_form.html
│   │   ├── amenity_booking_list.html
│   │   ├── amenity_booking_approve.html
│   │   └── visitor_list.html
│   ├── resident/
│   │   ├── resident_dashboard.html
│   │   ├── profile.html
│   │   ├── profile_edit.html
│   │   ├── bills_list.html
│   │   ├── bills_pay.html
│   │   ├── complaints_list.html
│   │   ├── complaints_create.html
│   │   ├── complaints_detail.html
│   │   ├── amenities_list.html
│   │   ├── amenities_book.html
│   │   ├── bookings_list.html
│   │   ├── notices_list.html
│   │   ├── notices_detail.html
│   │   ├── visitor_approvals.html
│   │   └── visitor_log.html
│   ├── staff/
│   │   ├── staff_dashboard.html
│   │   ├── tasks_list.html
│   │   ├── tasks_update.html
│   │   ├── complaints_list.html
│   │   ├── complaints_status.html
│   │   ├── visitors_list.html
│   │   ├── visitors_entry.html
│   │   └── visitors_exit.html
│   └── visitor/
│       ├── entry_registration.html
│       └── entry_form.html
└── (existing templates)


USAGE NOTES:
1. All templates extend base.html
2. Use {% load crispy_forms_tags %} for forms
3. Use Bootstrap 5 classes
4. Replace hardcoded values with template variables
5. Use {% url %} tag for URLs
6. Use {% for %} loops for lists
'''

print(TEMPLATE_STRUCTURE)
