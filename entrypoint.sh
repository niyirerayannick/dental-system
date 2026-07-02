#!/bin/sh
set -e

mkdir -p /app/media

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn dental_system.wsgi:application --bind 0.0.0.0:8000
