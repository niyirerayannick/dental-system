from django.conf import settings


from patients.models import PatientProfile


PATIENT_WELCOME_RW = """Muraho {full_name},

Murakoze kwiyandikisha muri {clinic_name}. Ikipe yacu, irimo {dentist_name}, yiteguye kubafasha kwita ku buzima bw'amenyo no mu kanwa.
"""


PATIENT_WELCOME_EN = """Hello {full_name},
Thank you for registering with {clinic_name}. Our team, including {dentist_name}, is ready to support your dental and oral health care."""


NEXT_APPOINTMENT_RW = """Muraho {full_name},

Gahunda yanyu muri {clinic_name} yakiriwe: {appointment_date} saa {appointment_time} hamwe na {dentist_name}. Tuzabamenyesha nimara kwemezwa."""


NEXT_APPOINTMENT_EN = """Hello {full_name},
Your appointment request at {clinic_name} has been received: {appointment_date} at {appointment_time} with {dentist_name}. We will notify you once it is confirmed."""


THANK_YOU_AFTER_SERVICE_RW = """Muraho {full_name},

Murakoze kugana {clinic_name}. Twishimiye ko mwitaweho na {dentist_name}. Mugize ikibazo cyangwa mukeneye ubujyanama, mwaduhamagara kuri {clinic_phone}."""


THANK_YOU_AFTER_SERVICE_EN = """Hello {full_name},
Thank you for visiting {clinic_name}. We are glad you were cared for by {dentist_name}. If you have any concern or need advice, please call {clinic_phone}."""


APPOINTMENT_CONFIRMED_RW = """Muraho {full_name},

Gahunda yanyu muri {clinic_name} yemejwe: {appointment_date} saa {appointment_time} hamwe na {dentist_name}. Niba mukeneye kuyihindura, muduhamagare kuri {clinic_phone}."""


APPOINTMENT_CONFIRMED_EN = """Hello {full_name},
Your appointment at {clinic_name} is confirmed: {appointment_date} at {appointment_time} with {dentist_name}. To reschedule, please call {clinic_phone}."""


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
    return getattr(patient, "preferred_language", PatientProfile.Language.KINYARWANDA) or PatientProfile.Language.KINYARWANDA


def _template_for_patient(template, patient):
    translations = TEMPLATE_TRANSLATIONS.get(template, {})
    return translations.get(_patient_language(patient), translations.get(PatientProfile.Language.KINYARWANDA, template))


def patient_welcome_message(patient, dentist_name="our dental team"):
    template = _template_for_patient(PATIENT_WELCOME, patient)
    return template.format(
        full_name=patient.user.full_name or patient.user.phone,
        dentist_name=dentist_name,
        clinic_name=settings.CLINIC_NAME,
    )


def appointment_message(template, appointment):
    selected_template = _template_for_patient(template, appointment.patient)
    return selected_template.format(
        full_name=appointment.patient.user.full_name or appointment.patient.user.phone,
        dentist_name=str(appointment.dentist),
        appointment_date=appointment.appointment_date.strftime("%Y-%m-%d"),
        appointment_time=appointment.appointment_time.strftime("%H:%M"),
        clinic_name=settings.CLINIC_NAME,
        clinic_phone=settings.CLINIC_PHONE,
    )
