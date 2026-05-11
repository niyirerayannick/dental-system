# Dental Appointment Booking and Patient Management System

A Django and Tailwind CSS system for managing patients, dentists, appointments, treatments, invoices, and role-based dashboards.

## Features

- Custom email-based user model
- Role-based access control for `ADMIN`, `DENTIST`, `RECEPTIONIST`, and `PATIENT`
- Patient appointment booking with dentist availability, daily capacity, and duplicate slot prevention
- Dentist and receptionist appointment approval, cancellation, and completion
- Treatment records, invoice tracking, exports, and custom dashboard CRUD modals
- Django Templates with compiled Tailwind CSS
- Docker/Coolify-ready deployment with PostgreSQL, WhiteNoise, and Gunicorn

## Local Development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

For local SQLite development, set:

```env
DEBUG=True
SECRET_KEY=local-dev-secret
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
DATABASE_URL=
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

Run:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

## Tailwind CSS

The compiled CSS is committed at `static/css/styles.css`, so Docker deployment does not require Node.js.

To rebuild CSS locally:

```bash
npm install
npm run build:css
```

## Coolify Deployment

1. Push the project to GitHub.
2. In Coolify, create a PostgreSQL database.
3. Copy the PostgreSQL connection string.
4. Create a new Coolify application from the GitHub repository.
5. Choose Dockerfile build.
6. Add environment variables:

```env
SECRET_KEY=use-a-long-random-secret
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
DATABASE_URL=postgres://username:password@host:5432/database_name
TIME_ZONE=Africa/Kigali
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
USE_X_FORWARDED_HOST=True
SECURE_PROXY_SSL_HEADER=True
```

7. Set your domain in Coolify and enable SSL.
8. Deploy.

The container starts with `entrypoint.sh`, which automatically runs:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn dental_system.wsgi:application --bind 0.0.0.0:8000
```

## Create A Superuser On Coolify

Use Coolify's terminal/execute command feature:

```bash
python manage.py createsuperuser
```

## Health Check

Coolify can check:

```text
/health/
```

Expected response:

```json
{"status": "ok"}
```

## Local Docker Production Test

```bash
docker compose up --build
```

Open:

```text
http://localhost:8000/health/
```

The compose file runs a `web` container and a local PostgreSQL container.

## Static And Media Files

- Static files are collected to `staticfiles/`.
- WhiteNoise serves static files in production.
- Media uploads are stored in `media/`.
- In Coolify, add persistent storage for `/app/media` if user-uploaded profile images must survive redeploys.

## Troubleshooting Deployment

- Check Coolify logs if the app does not start.
- Confirm `SECRET_KEY` is set and not the insecure fallback.
- Confirm `ALLOWED_HOSTS` includes your deployed domain.
- Confirm `CSRF_TRUSTED_ORIGINS` includes `https://yourdomain.com`.
- Confirm `DATABASE_URL` points to the Coolify PostgreSQL service.
- If SSL redirect loops occur, keep `SECURE_PROXY_SSL_HEADER=True` and `USE_X_FORWARDED_HOST=True`.
- If static files are missing, check that `collectstatic` completed successfully.

## Security Notes

- Use `DEBUG=False` in production.
- Use HTTPS with secure cookies in production.
- Do not commit a real `.env`.
- PostgreSQL is recommended for production.
- SQLite fallback is only for local development.
