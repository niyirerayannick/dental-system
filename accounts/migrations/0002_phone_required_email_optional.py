import re

from django.db import migrations, models


def _normalize(raw):
    if not raw:
        return raw
    cleaned = re.sub(r'[\s\-\(\)]', '', str(raw)).lstrip('+')
    if len(cleaned) == 10 and cleaned.startswith('07'):
        return '+250' + cleaned[1:]
    if len(cleaned) == 12 and cleaned.startswith('250'):
        return '+' + cleaned
    return raw


def normalise_empty_emails(apps, schema_editor):
    """Convert empty-string emails to NULL."""
    User = apps.get_model("accounts", "User")
    User.objects.filter(email="").update(email=None)


def fix_phones(apps, schema_editor):
    """
    Normalize all phones to +2507XXXXXXXX.
    Assign unique placeholders to blank phones and to any duplicates.
    """
    User = apps.get_model("accounts", "User")
    seen = {}

    for user in User.objects.all().order_by("pk"):
        phone = _normalize(user.phone) if user.phone else ""
        if not phone or phone in seen:
            phone = f"+25070000{user.pk:04d}"
        seen[phone] = True
        if phone != user.phone:
            user.phone = phone
            user.save(update_fields=["phone"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        # 1. Make email nullable (existing rows keep their values)
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
        # 2. Convert empty-string emails to NULL
        migrations.RunPython(normalise_empty_emails, migrations.RunPython.noop),
        # 3. Temporarily drop unique constraint and expand to allow blanks
        migrations.AlterField(
            model_name="user",
            name="phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        # 4. Normalize phones + resolve blanks and duplicates
        migrations.RunPython(fix_phones, migrations.RunPython.noop),
        # 5. Make phone required and unique
        migrations.AlterField(
            model_name="user",
            name="phone",
            field=models.CharField(max_length=20, unique=True),
        ),
    ]
