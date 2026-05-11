from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone


BOOKED_STATUSES = ("pending", "approved", "completed")


def dentist_available_days(dentist):
    return {day.strip().lower() for day in dentist.available_days.split(",") if day.strip()}


def is_dentist_active(dentist):
    return bool(dentist and dentist.user.role == dentist.user.Role.DENTIST and dentist.user.is_active and dentist.is_available)


def slot_time_range(date_value, time_value, duration_minutes):
    start = datetime.combine(date_value, time_value)
    return start, start + timedelta(minutes=duration_minutes)


def time_overlaps_break(dentist, date_value, time_value):
    if not dentist.break_start_time or not dentist.break_end_time:
        return False
    slot_start, slot_end = slot_time_range(date_value, time_value, dentist.appointment_duration)
    break_start = datetime.combine(date_value, dentist.break_start_time)
    break_end = datetime.combine(date_value, dentist.break_end_time)
    return slot_start < break_end and slot_end > break_start


def booked_appointments(dentist, date_value):
    from .models import Appointment

    return Appointment.objects.filter(
        dentist=dentist,
        appointment_date=date_value,
        status__in=BOOKED_STATUSES,
    )


def booked_times(dentist, date_value, exclude_pk=None):
    qs = booked_appointments(dentist, date_value)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return set(qs.values_list("appointment_time", flat=True))


def booked_count(dentist, date_value, exclude_pk=None):
    qs = booked_appointments(dentist, date_value)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.count()


def is_fully_booked(dentist, date_value, exclude_pk=None):
    return booked_count(dentist, date_value, exclude_pk=exclude_pk) >= dentist.max_patients_per_day


def is_working_date(dentist, date_value):
    return date_value.strftime("%A").lower() in dentist_available_days(dentist)


def generate_time_slots(dentist, date_value, include_booked=False, exclude_pk=None):
    if not is_dentist_active(dentist) or not is_working_date(dentist, date_value):
        return []

    booked = booked_times(dentist, date_value, exclude_pk=exclude_pk)
    now = timezone.localtime()
    cursor = datetime.combine(date_value, dentist.available_from)
    end = datetime.combine(date_value, dentist.available_to)
    step = timedelta(minutes=dentist.appointment_duration)
    slots = []

    while cursor + step <= end:
        slot_time = cursor.time()
        is_past = date_value == now.date() and cursor <= now.replace(tzinfo=None)
        is_booked = slot_time in booked
        is_break = time_overlaps_break(dentist, date_value, slot_time)
        if not is_past and not is_break and (include_booked or not is_booked):
            slots.append(slot_time.strftime("%H:%M"))
        cursor += step

    if is_fully_booked(dentist, date_value, exclude_pk=exclude_pk):
        return []
    return slots


def availability_summary(dentist, days=60):
    today = timezone.localdate()
    available_dates = []
    fully_booked_dates = []

    for offset in range(days):
        date_value = today + timedelta(days=offset)
        iso_date = date_value.isoformat()
        if not is_dentist_active(dentist) or not is_working_date(dentist, date_value):
            continue
        if is_fully_booked(dentist, date_value) or not generate_time_slots(dentist, date_value):
            fully_booked_dates.append(iso_date)
        else:
            available_dates.append(iso_date)

    return {
        "available_days": sorted(dentist_available_days(dentist)),
        "available_from": dentist.available_from.strftime("%H:%M"),
        "available_to": dentist.available_to.strftime("%H:%M"),
        "appointment_duration": dentist.appointment_duration,
        "max_patients_per_day": dentist.max_patients_per_day,
        "break_start_time": dentist.break_start_time.strftime("%H:%M") if dentist.break_start_time else None,
        "break_end_time": dentist.break_end_time.strftime("%H:%M") if dentist.break_end_time else None,
        "is_available": is_dentist_active(dentist),
        "fully_booked_dates": fully_booked_dates,
        "available_dates_next_60_days": available_dates,
    }


def validate_appointment_slot(appointment):
    errors = {}
    dentist = appointment.dentist
    date_value = appointment.appointment_date
    time_value = appointment.appointment_time

    if not dentist:
        errors["dentist"] = "Select a dentist."
    elif not is_dentist_active(dentist):
        errors["dentist"] = "Select an active available dentist."

    if date_value:
        today = timezone.localdate()
        if date_value < today:
            errors["appointment_date"] = "Appointment date cannot be in the past."
        elif dentist and not is_working_date(dentist, date_value):
            errors["appointment_date"] = "This dentist is not available on this day."

    if dentist and date_value and time_value:
        now = timezone.localtime()
        slot_start, slot_end = slot_time_range(date_value, time_value, dentist.appointment_duration)
        work_start = datetime.combine(date_value, dentist.available_from)
        work_end = datetime.combine(date_value, dentist.available_to)
        if date_value == now.date() and slot_start <= now.replace(tzinfo=None):
            errors["appointment_time"] = "Appointment time cannot be in the past."
        elif slot_start < work_start or slot_end > work_end:
            errors["appointment_time"] = "Appointment time is outside the dentist's available hours."
        elif time_overlaps_break(dentist, date_value, time_value):
            errors["appointment_time"] = "Appointment time falls during the dentist's break."
        elif time_value in booked_times(dentist, date_value, exclude_pk=appointment.pk):
            errors["appointment_time"] = "This dentist already has an appointment at the selected date and time."
        elif is_fully_booked(dentist, date_value, exclude_pk=appointment.pk):
            errors["appointment_date"] = "This date is fully booked."

    if errors:
        raise ValidationError(errors)
