from django.db import migrations

CATEGORIES = [
    {"name": "Preventive Care", "icon": "shield", "description": "Routine care to prevent dental problems"},
    {"name": "Restorative Dentistry", "icon": "build", "description": "Repair and restore damaged teeth"},
    {"name": "Cosmetic Dentistry", "icon": "auto_awesome", "description": "Improve the appearance of your smile"},
    {"name": "Orthodontics", "icon": "straighten", "description": "Correct misaligned teeth and jaws"},
    {"name": "Oral Surgery", "icon": "surgical", "description": "Surgical procedures for complex dental issues"},
    {"name": "Periodontics", "icon": "healing", "description": "Treatment of gum diseases and conditions"},
]

SERVICES = [
    {
        "category": "Preventive Care",
        "name": "Dental Cleaning & Polishing",
        "description": "Professional removal of plaque and tartar with tooth polishing.",
        "duration_minutes": 45,
        "base_price": "30.00",
        "icon": "cleaning_services",
    },
    {
        "category": "Preventive Care",
        "name": "Fluoride Treatment",
        "description": "Fluoride application to strengthen enamel and prevent cavities.",
        "duration_minutes": 20,
        "base_price": "15.00",
        "icon": "water_drop",
    },
    {
        "category": "Preventive Care",
        "name": "Dental Exam & X-Ray",
        "description": "Comprehensive oral examination with digital radiographs.",
        "duration_minutes": 30,
        "base_price": "25.00",
        "icon": "radiology",
    },
    {
        "category": "Restorative Dentistry",
        "name": "Tooth Filling (Composite)",
        "description": "Tooth-colored resin filling for cavities and minor fractures.",
        "duration_minutes": 45,
        "base_price": "50.00",
        "icon": "build",
    },
    {
        "category": "Restorative Dentistry",
        "name": "Dental Crown Fitting",
        "description": "Custom crown placement to restore a damaged or weakened tooth.",
        "duration_minutes": 90,
        "base_price": "200.00",
        "icon": "workspace_premium",
    },
    {
        "category": "Cosmetic Dentistry",
        "name": "Teeth Whitening",
        "description": "In-office bleaching treatment to brighten your smile by several shades.",
        "duration_minutes": 60,
        "base_price": "80.00",
        "icon": "wb_sunny",
    },
    {
        "category": "Cosmetic Dentistry",
        "name": "Dental Veneers",
        "description": "Thin porcelain shells bonded to the front of teeth for a flawless look.",
        "duration_minutes": 120,
        "base_price": "350.00",
        "icon": "auto_awesome",
    },
    {
        "category": "Orthodontics",
        "name": "Braces Consultation & Installation",
        "description": "Initial consultation plus fitting of traditional or ceramic braces.",
        "duration_minutes": 90,
        "base_price": "500.00",
        "icon": "straighten",
    },
    {
        "category": "Oral Surgery",
        "name": "Tooth Extraction (Simple)",
        "description": "Removal of a visible, fully erupted tooth under local anaesthesia.",
        "duration_minutes": 30,
        "base_price": "40.00",
        "icon": "surgical",
    },
    {
        "category": "Oral Surgery",
        "name": "Wisdom Tooth Removal",
        "description": "Surgical extraction of impacted or partially erupted wisdom teeth.",
        "duration_minutes": 60,
        "base_price": "120.00",
        "icon": "healing",
    },
    {
        "category": "Periodontics",
        "name": "Gum Disease Treatment (Scaling & Root Planing)",
        "description": "Deep cleaning below the gumline to treat gum disease and restore gum health.",
        "duration_minutes": 75,
        "base_price": "90.00",
        "icon": "medication",
    },
]


def seed_data(apps, schema_editor):
    ServiceCategory = apps.get_model("services", "ServiceCategory")
    DentalService = apps.get_model("services", "DentalService")

    cat_map = {}
    for cat_data in CATEGORIES:
        cat, _ = ServiceCategory.objects.get_or_create(name=cat_data["name"], defaults=cat_data)
        cat_map[cat.name] = cat

    for svc_data in SERVICES:
        data = dict(svc_data)
        cat_name = data.pop("category")
        DentalService.objects.get_or_create(
            name=data["name"],
            category=cat_map[cat_name],
            defaults=data,
        )


def remove_data(apps, schema_editor):
    ServiceCategory = apps.get_model("services", "ServiceCategory")
    ServiceCategory.objects.filter(name__in=[c["name"] for c in CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_data, remove_data),
    ]
