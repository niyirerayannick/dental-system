import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DentistProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("specialization", models.CharField(max_length=120)),
                ("license_number", models.CharField(max_length=80, unique=True)),
                (
                    "available_days",
                    models.CharField(
                        help_text="Comma-separated days, for example: Monday,Tuesday,Wednesday",
                        max_length=120,
                    ),
                ),
                ("available_from", models.TimeField()),
                ("available_to", models.TimeField()),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dentist_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["user__last_name", "user__first_name"]},
        ),
    ]
