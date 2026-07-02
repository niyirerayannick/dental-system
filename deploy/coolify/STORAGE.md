# Coolify storage setup (dentcare.rw)

## PostgreSQL

1. Create a PostgreSQL database in Coolify.
2. Copy the internal connection string.
3. Set `DATABASE_URL` on the application service, for example:

```env
DATABASE_URL=postgres://user:password@postgres-host:5432/dental
```

`DEBUG` must be `False` in production. SQLite is blocked when `DEBUG=False`.

## Persistent media volume

Uploaded files must not live inside the disposable container layer.

| Setting | Value |
|---------|-------|
| Host source path | `/var/www/dentalcare/media` |
| Container destination | `/app/media` |

### One-time host setup

```bash
sudo mkdir -p /var/www/dentalcare/media
sudo chown -R 1000:1000 /var/www/dentalcare/media
sudo chmod -R 775 /var/www/dentalcare/media
```

Adjust the UID/GID if your container runs as a different user.

### Coolify UI

1. Open the application in Coolify.
2. Go to **Persistent Storage**.
3. Add a volume:
   - **Source path**: `/var/www/dentalcare/media`
   - **Destination path**: `/app/media`
4. Redeploy.

Django settings:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # resolves to /app/media in the container
```

## Static files

Static assets are collected into `/app/staticfiles` on each deploy:

```bash
python manage.py collectstatic --noinput
```

WhiteNoise serves `/static/` from the container. Uploaded media is separate.

## Serving `/media/`

### Option A — Coolify proxy to Django (simplest)

Keep `SERVE_MEDIA=True`. Coolify forwards `/media/...` to Gunicorn; Django reads files from the mounted volume.

### Option B — Edge proxy serves public media from disk

Set `SERVE_MEDIA=False` and use `deploy/caddy/Caddyfile.example` or `deploy/nginx/media.conf.example`.

Route `/media/ask_doctor/attachments/` through Django so private files stay protected.

## Verify after deploy

```bash
python manage.py check_media_files
python manage.py check_media_files --deploy-check
```

If `--deploy-check` fails with `persistent volume mounted: no`, uploads will disappear on redeploy.

Manual test:

1. Upload a service image in the admin dashboard.
2. On the host: `ls /var/www/dentalcare/media/services/`
3. Open `https://dentcare.rw/media/services/<filename>`
4. Redeploy the app.
5. Confirm the same URL still works.

## Photos lost after redeploy?

The database only stores the **file path** (for example `services/photo.jpg`). The actual image bytes live on disk under `/app/media`.

Without a Coolify volume, redeploy replaces the container and deletes those files. PostgreSQL keeps the paths, so images look broken.

### Fix (do this now)

1. SSH into the Coolify server.
2. Create the host folder:

```bash
sudo mkdir -p /var/www/dentalcare/media
sudo chown -R 1000:1000 /var/www/dentalcare/media
sudo chmod -R 775 /var/www/dentalcare/media
```

3. In Coolify → your app → **Persistent Storage** → add:

| Source | Destination |
|--------|-------------|
| `/var/www/dentalcare/media` | `/app/media` |

4. Redeploy.
5. In Coolify terminal run:

```bash
python manage.py check_media_files --deploy-check
```

You should see `persistent volume mounted: yes`.

6. Re-upload service images that were lost (unless you have a backup of `/var/www/dentalcare/media` to restore).

### Confirm mount inside container

```bash
grep " /app/media " /proc/mounts
```

If this prints nothing, the volume is not attached.
