from django.db import models
from django.utils.text import slugify


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default="medical_services")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "service categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class DentalService(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="services")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=30, help_text="Duration in minutes")
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    icon = models.CharField(max_length=50, default="medical_services")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category__name", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "dental-service"
            slug = base_slug
            counter = 2
            while DentalService.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
