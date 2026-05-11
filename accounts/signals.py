from django.db.models.signals import post_save
from django.dispatch import receiver

from dentists.models import DentistProfile
from .models import User


@receiver(post_save, sender=User)
def create_dentist_profile_for_dentist_user(sender, instance, **kwargs):
    DentistProfile.ensure_for_user(instance)
