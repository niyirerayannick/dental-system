from django.conf import settings

from patients.models import PatientProfile


PRIMARY_DENTIST_NAME = "Dr. Igiraneza Boaz"


PATIENT_WELCOME_RW = """Muraho {full_name},
Murakoze guhitamo serivisi z’ishami ryita ku buzima bw’amenyo n’indwara zo mu kanwa, murakirwa na {dentist_name}.
Muri {clinic_name}, ubuzima bwiza bwanyu ni intego yacu. Murakoze kutugirira icyizere."""


PATIENT_WELCOME_EN = """Hello {full_name},
Thank you for choosing our dental and oral health services. You will be welcomed by {dentist_name}.
At {clinic_name}, your health and wellbeing are our priority. Thank you for trusting us."""


NEXT_APPOINTMENT_RW = """Muraho {full_name},
Gahunda yanyu yo kubonana na muganga {dentist_name} ni kuwa {appointment_date} saa {appointment_time} muri {clinic_name}.
Murakoze guhitamo serivisi z’ishami ryita ku buzima bw’amenyo n’indwara zo mu kanwa.
Mugize impamvu ituma muhindura gahunda, mwaduhamagara kuri {clinic_phone}."""


NEXT_APPOINTMENT_EN = """Hello {full_name},
Your next appointment with {dentist_name} is on {appointment_date} at {appointment_time} at {clinic_name}.
Thank you for choosing our dental and oral health services.
If you need to reschedule, please call {clinic_phone}."""


THANK_YOU_AFTER_SERVICE_RW = """Muraho {full_name},
Murakoze guhitamo serivisi z’ishami ryita ku menyo n’indwara zo mu kanwa muri {clinic_name}. Mwitaweho na {dentist_name}.
Ubuzima bwanyu ni intego yacu. Murakoze cyane.
Mugize ikibazo cyangwa mukeneye ubujyanama, mwaduhamagara kuri {clinic_phone}."""


THANK_YOU_AFTER_SERVICE_EN = """Hello {full_name},
Thank you for choosing dental and oral health services at {clinic_name}. You were cared for by {dentist_name}.
Your health is our priority. Thank you very much.
If you have any concern or need advice, please call {clinic_phone}."""


APPOINTMENT_CONFIRMED_RW = """Muraho {full_name},
Gahunda mwasabye yo kubonana na muganga {dentist_name} kuwa {appointment_date} saa {appointment_time} yemejwe.
Murakoze guhitamo serivisi z’ishami ryita ku buzima bw’amenyo n’indwara zo mu kanwa muri {clinic_name}.
Mugize impamvu ituma muhindura gahunda, mwaduhamagara kuri {clinic_phone}."""


APPOINTMENT_CONFIRMED_EN = """Hello {full_name},
Your appointment with {dentist_name} on {appointment_date} at {appointment_time} has been confirmed.
Thank you for choosing dental and oral health services at {clinic_name}.
If you need to reschedule, please call {clinic_phone}."""


PATIENT_WELCOME = PATIENT_WELCOME_RW
NEXT_APPOINTMENT = NEXT_APPOINTMENT_RW
THANK_YOU_AFTER_SERVICE = THANK_YOU_AFTER_SERVICE_RW
APPOINTMENT_CONFIRMED = APPOINTMENT_CONFIRMED_RW


TEMPLATE_TRANSLATIONS = {
    PATIENT_WELCOME_RW: {
        PatientProfile.Language.KINYARWANDA: PATIENT_WELCOME_RW,
        PatientProfile.Language.ENGLISH: PATIENT_WELCOME_EN,
    },
    NEXT_APPOINTMENT_RW: {
        PatientProfile.Language.KINYARWANDA: NEXT_APPOINTMENT_RW,
        PatientProfile.Language.ENGLISH: NEXT_APPOINTMENT_EN,
    },
    THANK_YOU_AFTER_SERVICE_RW: {
        PatientProfile.Language.KINYARWANDA: THANK_YOU_AFTER_SERVICE_RW,
        PatientProfile.Language.ENGLISH: THANK_YOU_AFTER_SERVICE_EN,
    },
    APPOINTMENT_CONFIRMED_RW: {
        PatientProfile.Language.KINYARWANDA: APPOINTMENT_CONFIRMED_RW,
        PatientProfile.Language.ENGLISH: APPOINTMENT_CONFIRMED_EN,
    },
}


def _patient_language(patient):
    return (
        getattr(patient, "preferred_language", PatientProfile.Language.KINYARWANDA)
        or PatientProfile.Language.KINYARWANDA
    )


def _template_for_patient(template, patient):
    translations = TEMPLATE_TRANSLATIONS.get(template, {})
    return translations.get(
        _patient_language(patient),
        translations.get(PatientProfile.Language.KINYARWANDA, template),
    )


def _patient_full_name(patient):
    return patient.user.full_name or patient.user.phone


def _format_appointment_date(date_obj, language):
    if language == PatientProfile.Language.KINYARWANDA:
        return date_obj.strftime("%d/%m/%Y")
    return date_obj.strftime("%B %d, %Y")


def _format_appointment_time(time_obj):
    return time_obj.strftime("%H:%M")


def patient_welcome_message(patient, dentist_name=PRIMARY_DENTIST_NAME):
    template = _template_for_patient(PATIENT_WELCOME, patient)
    return template.format(
        full_name=_patient_full_name(patient),
        dentist_name=PRIMARY_DENTIST_NAME,
        clinic_name=settings.CLINIC_NAME,
    )


def appointment_message(template, appointment):
    language = _patient_language(appointment.patient)
    selected_template = _template_for_patient(template, appointment.patient)

    return selected_template.format(
        full_name=_patient_full_name(appointment.patient),
        dentist_name=PRIMARY_DENTIST_NAME,
        appointment_date=_format_appointment_date(
            appointment.appointment_date,
            language,
        ),
        appointment_time=_format_appointment_time(appointment.appointment_time),
        clinic_name=settings.CLINIC_NAME,
        clinic_phone=settings.CLINIC_PHONE,
    )