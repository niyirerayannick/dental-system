#!/bin/sh
set -e

mkdir -p /app/media

if [ -f /proc/mounts ] && ! grep -q " /app/media " /proc/mounts; then
  echo "============================================================"
  echo "WARNING: /app/media is NOT a persistent volume."
  echo "Uploaded photos will be LOST on every redeploy."
  echo ""
  echo "Fix in Coolify -> Persistent Storage:"
  echo "  Source path:      /var/www/dentalcare/media"
  echo "  Destination path: /app/media"
  echo ""
  echo "On the host run once:"
  echo "  sudo mkdir -p /var/www/dentalcare/media"
  echo "  sudo chmod -R 775 /var/www/dentalcare/media"
  echo "============================================================"
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${DEBUG}" = "False" ] || [ "${DEBUG}" = "false" ] || [ "${DEBUG}" = "0" ]; then
  python manage.py check_media_files --deploy-check || true
fi

exec gunicorn dental_system.wsgi:application --bind 0.0.0.0:8000
