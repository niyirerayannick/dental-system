from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0003_dentalservice_slug"),
    ]

    operations = [
        migrations.AddField(
            model_name="dentalservice",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="services/images/"),
        ),
        migrations.AddField(
            model_name="dentalservice",
            name="short_description",
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AddField(
            model_name="dentalservice",
            name="full_description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="dentalservice",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="dentalservice",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
