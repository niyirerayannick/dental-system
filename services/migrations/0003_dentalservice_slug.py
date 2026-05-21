from django.db import migrations, models
from django.utils.text import slugify


def populate_service_slugs(apps, schema_editor):
    DentalService = apps.get_model("services", "DentalService")
    used = set()
    for service in DentalService.objects.all().order_by("pk"):
        base_slug = slugify(service.name) or f"dental-service-{service.pk}"
        slug = base_slug
        counter = 2
        while slug in used or DentalService.objects.filter(slug=slug).exclude(pk=service.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        service.slug = slug
        service.save(update_fields=["slug"])
        used.add(slug)


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0002_seed_initial_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="dentalservice",
            name="slug",
            field=models.SlugField(blank=True, max_length=180, null=True, unique=True),
        ),
        migrations.RunPython(populate_service_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="dentalservice",
            name="slug",
            field=models.SlugField(blank=True, max_length=180, unique=True),
        ),
    ]
