import logging

from appointments.models import Appointment
from .message_templates import (
    APPOINTMENT_CONFIRMED,
    NEXT_APPOINTMENT,
    THANK_YOU_AFTER_SERVICE,
    appointment_message,
    patient_welcome_message,
)
from .services.twilio_service import send_preferred

logger = logging.getLogger(__name__)


def _patient_phone(patient):
    return getattr(patient.user, "phone", "")


def notify_patient_created(patient, dentist_name="our dental team"):
    try:
        return send_preferred(
            _patient_phone(patient),
            patient_welcome_message(patient, dentist_name=dentist_name),
            patient=patient,
        )
    except Exception:
        logger.exception("Failed to queue patient welcome notification")
        return {"ok": False, "error": "Unexpected notification failure"}


def notify_appointment_created(appointment):
    try:
        return send_preferred(
            _patient_phone(appointment.patient),
            appointment_message(NEXT_APPOINTMENT, appointment),
            patient=appointment.patient,
            appointment=appointment,
        )
    except Exception:
        logger.exception("Failed to queue appointment notification")
        return {"ok": False, "error": "Unexpected notification failure"}


def notify_appointment_confirmed(appointment):
    try:
        return send_preferred(
            _patient_phone(appointment.patient),
            appointment_message(APPOINTMENT_CONFIRMED, appointment),
            patient=appointment.patient,
            appointment=appointment,
        )
    except Exception:
        logger.exception("Failed to queue appointment confirmation notification")
        return {"ok": False, "error": "Unexpected notification failure"}


def notify_service_completed(appointment):
    try:
        return send_preferred(
            _patient_phone(appointment.patient),
            appointment_message(THANK_YOU_AFTER_SERVICE, appointment),
            patient=appointment.patient,
            appointment=appointment,
        )
    except Exception:
        logger.exception("Failed to queue service completion notification")
        return {"ok": False, "error": "Unexpected notification failure"}


def notify_appointment_status_change(appointment, old_status=None):
    if old_status == appointment.status:
        return None
    if appointment.status == Appointment.Status.APPROVED:
        return notify_appointment_confirmed(appointment)
    if appointment.status == Appointment.Status.COMPLETED:
        return notify_service_completed(appointment)
    return None
