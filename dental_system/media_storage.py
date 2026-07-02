from pathlib import Path


COOLIFY_MEDIA_HOST_PATH = "/var/www/dentalcare/media"
COOLIFY_MEDIA_CONTAINER_PATH = "/app/media"


def is_media_mount_persistent(media_root=None):
    """Return True when media_root is a separate mount (bind volume), False when ephemeral."""
    media_root = Path(media_root or COOLIFY_MEDIA_CONTAINER_PATH)
    proc_mounts = Path("/proc/mounts")
    if not proc_mounts.exists():
        return None

    target = str(media_root.resolve())
    for line in proc_mounts.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == target:
            return True
    return False
