from django.contrib import admin
from .models import DentalService, ServiceCategory

admin.site.register(ServiceCategory)
admin.site.register(DentalService)
