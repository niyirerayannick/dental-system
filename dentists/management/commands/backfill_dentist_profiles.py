from django.core.management.base import BaseCommand

from accounts.models import User
from dentists.models import DentistProfile


class Command(BaseCommand):
    help = "Create missing dentist profiles for active and inactive users with the DENTIST role."

    def handle(self, *args, **options):
        created = 0
        for user in User.objects.filter(role=User.Role.DENTIST):
            existed = DentistProfile.objects.filter(user=user).exists()
            DentistProfile.ensure_for_user(user)
            if not existed:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} missing dentist profile(s)."))
