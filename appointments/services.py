from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone


BOOKED_STATUSES = ("pending", "approved", "completed")


# ── Per-day schedule helpers ────────────────────────────────────────────────

def get_day_schedule(dentist, date_value):
    """Return DentistDaySchedule for the weekday of date_value, or None."""
    day_name = date_value.strftime("%A").lower()
    return dentist.day_schedules.filter(day=day_name).first()


def _day_start(dentist, date_value):
    sched = get_day_schedule(dentist, date_value)
    return sched.start_time if sched else dentist.available_from


def _day_end(dentist, date_value):
    sched = get_day_schedule(dentist, date_value)
    return sched.end_time if sched else dentist.available_to


def _day_break_start(dentist, date_value):
    sched = get_day_schedule(dentist, date_value)
    if sched:
        return sched.break_start
    return dentist.break_start_time


def _day_break_end(dentist, date_value):
    sched = get_day_schedule(dentist, date_value)
    if sched:
        return sched.break_end
    return dentist.break_end_time


# ── Legacy helpers (kept for fallback) ──────────────────────────────────────

def dentist_available_days(dentist):
    """Return set of lowercase day names from day_schedules or old available_days field."""
    if dentist.day_schedules.exists():
        return set(dentist.day_schedules.values_list("day", flat=True))
    return {day.strip().lower() for day in dentist.available_days.split(",") if day.strip()}


def is_dentist_active(dentist):
    return bool(dentist and dentist.user.role == dentist.user.Role.DENTIST and dentist.user.is_active and dentist.is_available)


def is_working_date(dentist, date_value):
    day_name = date_value.strftime("%A").lower()
    if dentist.day_schedules.exists():
        return dentist.day_schedules.filter(day=day_name).exists()
    return day_name in dentist_available_days(dentist)


# ── Slot generation ──────────────────────────────────────────────────────────

def slot_time_range(date_value, time_value, duration_minutes):
    start = datetime.combine(date_value, time_value)
    return start, start + timedelta(minutes=duration_minutes)


def time_overlaps_break(dentist, date_value, time_value):
    bstart = _day_break_start(dentist, date_value)
    bend = _day_break_end(dentist, date_value)
    if not bstart or not bend:
        return False
    slot_start, slot_end = slot_time_range(date_value, time_value, dentist.appointment_duration)
    break_start = datetime.combine(date_value, bstart)
    break_end = datetime.combine(date_value, bend)
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


def generate_time_slots(dentist, date_value, include_booked=False, exclude_pk=None):
    if not is_dentist_active(dentist) or not is_working_date(dentist, date_value):
        return []

    booked = booked_times(dentist, date_value, exclude_pk=exclude_pk)
    now = timezone.localtime()
    day_start = _day_start(dentist, date_value)
    day_end = _day_end(dentist, date_value)
    cursor = datetime.combine(date_value, day_start)
    end = datetime.combine(date_value, day_end)
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

    # Build per-day schedule info for API response
    day_schedules = {}
    for sched in dentist.day_schedules.all():
        day_schedules[sched.day] = {
            "start": sched.start_time.strftime("%H:%M"),
            "end": sched.end_time.strftime("%H:%M"),
            "break_start": sched.break_start.strftime("%H:%M") if sched.break_start else None,
            "break_end": sched.break_end.strftime("%H:%M") if sched.break_end else None,
        }

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
        "day_schedules": day_schedules,
        "appointment_duration": dentist.appointment_duration,
        "max_patients_per_day": dentist.max_patients_per_day,
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
        work_start = datetime.combine(date_value, _day_start(dentist, date_value))
        work_end = datetime.combine(date_value, _day_end(dentist, date_value))
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
