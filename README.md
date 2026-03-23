# 🏢 eSociety Management System

A full-stack **Django-based Society Management System** designed to manage residential communities efficiently.
It provides features like complaint tracking, billing & payments, visitor management, notifications, and a powerful admin dashboard.

---

## 🚀 Live Features

### 🔐 Authentication & Security

* User Signup & Login System
* Email Verification
* Forgot Password via Email
* Role-Based Access Control (Admin, Resident, Staff)
* Secure Authentication (Django built-in security)

---

### 👤 User Management

* Profile Update with Image Upload
* Role Assignment & Access Restriction
* User Activation / Deactivation

---

### 📊 Admin Dashboard

* Overview of Users, Complaints, Revenue
* Interactive Charts (Chart.js)
* Clean Sidebar Navigation UI

---

### 📢 Complaint Management

* Residents can submit complaints
* Upload images with complaints
* Admin can:

  * Change status (Pending / In Progress / Resolved)
  * Assign complaints
  * Add comments

---

### 💳 Billing & Payment

* Generate bills for residents
* Online Payment Integration (Stripe)
* Payment Status Tracking
* Invoice Generation

---

### 🔔 Notification System

* Real-time In-App Notifications
* Email Notifications
* Notification Bell UI

---

### 🚶 Visitor Management

* Visitor Entry System
* Approval / Rejection by Admin
* Visitor Logs

---

### 📢 Notice Board

* Admin can create notices
* Notices visible to all residents

---

### 🔍 Search & Pagination

* Search Users, Complaints, Bills
* Pagination for large data

---

### 📁 Reports

* Export data to CSV / Excel

---

### 🎨 UI/UX

* Responsive Design (Mobile Friendly)
* Bootstrap-based Clean UI
* Sidebar Dashboard Layout
* Modern Cards & Tables
* Dark Mode (Optional)

---

## 🛠️ Tech Stack

| Technology | Use                  |
| ---------- | -------------------- |
| Django     | Backend Framework    |
| Python     | Programming Language |
| Bootstrap  | Frontend UI          |
| SQLite     | Database             |
| Stripe API | Payment Integration  |
| Chart.js   | Dashboard Charts     |
| SMTP       | Email System         |

---

## 📂 Project Structure

```id="qkthsd"
e_society/
│
├── users/           # User authentication & profiles
├── complaints/      # Complaint system
├── payments/        # Billing & payments
├── visitors/        # Visitor management
├── notices/         # Notice board
├── templates/       # HTML templates
├── static/          # CSS, JS, images
├── media/           # Uploaded files
├── manage.py
└── db.sqlite3
```

---

## ⚙️ Setup Instructions (Run in 5 Steps)

### 1️⃣ Clone Repository

```bash id="blp7y7"
git clone https://github.com/GohilVijay07/e_socity.git
cd e_socity
```

---

### 2️⃣ Create Virtual Environment

```bash id="r1g3nm"
python -m venv venv
venv\Scripts\activate   # Windows
```

---

### 3️⃣ Install Dependencies

```bash id="n2wd5h"
pip install -r requirements.txt
```

---

### 4️⃣ Create `.env` File

Create a `.env` file in root folder and paste:

```id="b8l6hi"
SECRET_KEY=django-insecure-change-this-key
DEBUG=True

STRIPE_PUBLIC_KEY=your_stripe_public_key
STRIPE_SECRET_KEY=your_stripe_secret_key

EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_email_password
```

---

### 5️⃣ Run Project

```bash id="pg1c9m"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

👉 Open in browser: http://127.0.0.1:8000/

---

## 🔑 Default Routes

* Home: `/`
* Login: `/login`
* Admin Panel: `/admin`

---

## 🧪 Demo Flow

1. User Signup
2. Email Verification
3. Login
4. Raise Complaint
5. Admin Resolves Complaint
6. Generate Bill
7. Make Payment
8. Receive Notification

---

## 🔐 Security Notes

* Admin role cannot be selected during signup
* Role-based access protection implemented
* CSRF protection enabled

---

## 📸 Screenshots

*Add your screenshots here (Dashboard, Admin Panel, Payment, etc.)*

---

## 📈 Future Improvements

* Mobile App (Flutter / React Native)
* Real-time Chat System
* AI-based Complaint Categorization
* Cloud Deployment (AWS / Render)

---

## 👨‍💻 Author

**Vijay Gohil**

* GitHub: https://github.com/GohilVijay07
* LinkedIn: https://www.linkedin.com

---

## ⭐ Support

If you like this project, please give it a ⭐ on GitHub!

---
