import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("appointments", "0001_initial"),
        ("dentists", "0001_initial"),
        ("patients", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Treatment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("diagnosis", models.TextField()),
                ("treatment_plan", models.TextField()),
                ("prescription", models.TextField(blank=True)),
                ("treatment_date", models.DateField(default=django.utils.timezone.localdate)),
                (
                    "appointment",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treatment",
                        to="appointments.appointment",
                    ),
                ),
                (
                    "dentist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="treatments",
                        to="dentists.dentistprofile",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treatments",
                        to="patients.patientprofile",
                    ),
                ),
            ],
            options={"ordering": ["-treatment_date"]},
        ),
    ]
