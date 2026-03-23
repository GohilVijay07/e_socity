# 🏢 eSociety Management System

A full-stack Django-based web application for managing residential societies including billing, complaints, visitors, and notifications.

---

## 🚀 Run Project in 5 Steps

### 1️⃣ Clone Repository

```bash
git clone https://github.com/GohilVijay07/e_socity.git
cd e_socity
```

---

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Create `.env` File

Create a `.env` file in root folder and paste:

```
SECRET_KEY=django-insecure-change-this-key
DEBUG=True

STRIPE_PUBLIC_KEY=your_key
STRIPE_SECRET_KEY=your_key

EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_password
```

---

### 5️⃣ Run Project

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

👉 Open in browser: http://127.0.0.1:8000/

---

## 🔑 Features

* User Authentication (Login / Signup)
* Role-Based Access (Admin, Resident, Staff)
* Complaint Management System
* Online Payment Integration (Stripe)
* Notification System (Email + In-App)
* Visitor Management
* Notice Board
* Admin Dashboard with Charts
* Profile Management with Image Upload
* Search & Pagination
* CSV / Excel Reports

---

## ⚙️ Tech Stack

* Django (Python)
* Bootstrap
* SQLite
* Stripe API
* Chart.js

---

## 📌 Important Notes

* `.env` file required
* Stripe keys required for payment
* Email credentials required for notifications

---

## 👨‍💻 Author

Vijay Gohil
GitHub: https://github.com/GohilVijay07

---

## ⭐ Support

If you like this project, give it a ⭐ on GitHub!
