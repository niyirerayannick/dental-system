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

See `deploy/coolify/STORAGE.md` for the full PostgreSQL + persistent media guide.

1. Push the project to GitHub.
2. In Coolify, create a PostgreSQL database and copy the connection string.
3. On the host, prepare persistent media storage:

```bash
sudo mkdir -p /var/www/dentalcare/media
sudo chown -R 1000:1000 /var/www/dentalcare/media
sudo chmod -R 775 /var/www/dentalcare/media
```

4. Create a Coolify application from the GitHub repository (Dockerfile build).
5. Add **Persistent Storage**:
   - Source path: `/var/www/dentalcare/media`
   - Destination path: `/app/media`
6. Add environment variables:

```env
SECRET_KEY=use-a-long-random-secret
DEBUG=False
ALLOWED_HOSTS=dentcare.rw,www.dentcare.rw
CSRF_TRUSTED_ORIGINS=https://dentcare.rw,https://www.dentcare.rw
DATABASE_URL=postgres://username:password@host:5432/database_name
TIME_ZONE=Africa/Kigali
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
USE_X_FORWARDED_HOST=True
SECURE_PROXY_SSL_HEADER=True
SERVE_MEDIA=True
```

7. Set your domain in Coolify and enable SSL.
8. Deploy.

`DATABASE_URL` is required when `DEBUG=False`. SQLite is only used for local development.

The container starts with `entrypoint.sh`, which automatically runs:

```bash
mkdir -p /app/media
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

### Static files

- `STATIC_URL = /static/`
- `STATIC_ROOT = /app/staticfiles` in the container
- Collected on each deploy: `python manage.py collectstatic --noinput`
- **WhiteNoise** serves static files only. It does not serve uploaded media.

### Uploaded media (persistent)

- `MEDIA_URL = /media/`
- `MEDIA_ROOT = /app/media` in the container
- **Coolify volume** (required in production):
  - Host source: `/var/www/dentalcare/media`
  - Container destination: `/app/media`
- Without this mount, uploads are lost on redeploy.

### Serving `/media/`

**Option A (recommended for Coolify):** keep `SERVE_MEDIA=True`. Coolify proxies `/media/...` to Gunicorn; Django reads files from the mounted volume.

**Option B (edge proxy):** serve public files directly from `/var/www/dentalcare/media` using `deploy/caddy/Caddyfile.example` or `deploy/nginx/media.conf.example`. Route `/media/ask_doctor/attachments/` through Django for private files.

Production media checks:

```bash
python manage.py check_media_files
```

Expected production values:

```text
ENGINE: django.db.backends.postgresql
MEDIA_URL=/media/
MEDIA_ROOT=/app/media
media folder exists: yes
writable: yes
Coolify host source path: /var/www/dentalcare/media
Coolify container destination: /app/media
```

After uploading a service image:

1. Confirm the file exists on the host: `/var/www/dentalcare/media/services/`
2. Open `https://dentcare.rw/media/services/<filename>`
3. Redeploy and confirm the URL still works

Ask Doctor attachments are stored under `/app/media/ask_doctor/attachments/` and are permission-checked by the Django media route.

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
