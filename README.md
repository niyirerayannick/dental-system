# Dental Appointment Booking and Patient Management System

A Django and Tailwind CSS system for managing patients, dentists, appointments, treatments, invoices, and role-based dashboards.

## Features

- Custom email-based user model
- Role-based access control for `ADMIN`, `DENTIST`, `RECEPTIONIST`, and `PATIENT`
- Patient appointment booking with duplicate slot prevention
- Dentist and receptionist appointment approval, cancellation, and completion
- Treatment records and invoice tracking
- Django Templates with Tailwind CSS
- PostgreSQL-ready settings with `python-decouple`
- Production-oriented security settings

## Requirements

- Python 3.11 or newer
- Node.js and npm for Tailwind CSS builds
- PostgreSQL for production or shared development
- SQLite for quick local development

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Create your local environment file:

```bash
copy .env.example .env
```

For local development, set these values in `.env`:

```env
DEBUG=True
DATABASE_ENGINE=sqlite
SQLITE_NAME=db.sqlite3
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
CSRF_COOKIE_HTTPONLY=True
SECURE_SSL_REDIRECT=False
```

For production, keep `DEBUG=False`, set a strong `SECRET_KEY`, configure your real domain in `ALLOWED_HOSTS`, and use HTTPS.

## Database Setup

The project supports SQLite and PostgreSQL.

SQLite local setup:

```env
DATABASE_ENGINE=sqlite
SQLITE_NAME=db.sqlite3
```

PostgreSQL setup:

```env
DATABASE_ENGINE=postgres
POSTGRES_DB=dental_system
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Run migrations:

```bash
python manage.py migrate
```

Create an admin user:

```bash
python manage.py createsuperuser
```

This project uses a custom user model. If you migrated an older version before the custom user model was added, back up or remove the old `db.sqlite3`, then run migrations again.

## Tailwind CSS Setup

Install frontend dependencies:

```bash
npm install
```

Build CSS once:

```bash
npm run build:css
```

Watch CSS during development:

```bash
npm run dev:css
```

Tailwind source file:

```text
static/src/input.css
```

Compiled CSS output:

```text
static/css/styles.css
```

## Run The Project

Start the development server:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000
```

Django admin:

```text
http://127.0.0.1:8000/admin/
```

## Roles

- `ADMIN`: system overview and admin access
- `DENTIST`: assigned appointments, appointment status updates, treatment records
- `RECEPTIONIST`: patient registration, appointment management, invoice viewing
- `PATIENT`: appointment booking, personal appointments, treatment history, invoices

## Security Notes

- All protected dashboard views require login.
- Role-specific pages use permission checks.
- Django CSRF middleware is enabled, and all POST forms include CSRF tokens.
- Password validation uses Django's built-in validators.
- Login redirects are checked to prevent unsafe external redirects.
- Production security settings are environment-driven.
- `DEBUG=False` should be used outside local development.
- Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` for your domain.
- Use HTTPS in production and enable secure cookies.

Recommended production `.env` values:

```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CSRF_COOKIE_HTTPONLY=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

Before deploying static files:

```bash
python manage.py collectstatic
```
