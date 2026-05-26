from django.conf import settings


PATIENT_WELCOME = """Kinyarwanda:
Muraho neza {full_name}, Murakoze guhitamo serivisi z'ishami ryita ku buzima bw'amenyo n'indwara zo mu kanwa, murakirwa na {dentist_name}.

Muri {clinic_name}, ubuzima bwiza bwanyu ni intego yacu. Murakoze kutugirira icyizere.

English:
Hello {full_name}, thank you for choosing our dental and oral health services. You will be welcomed by {dentist_name}.

At {clinic_name}, your health and wellbeing are our priority. Thank you for trusting us."""


NEXT_APPOINTMENT = """Kinyarwanda:
Ncuti {full_name}, gahunda itaha / rendez-vous yo kubonana na muganga {dentist_name} ni kuwa {appointment_date} saa {appointment_time} muri {clinic_name}.

Murakoze guhitamo serivisi z'ishami ryita ku buzima bw'amenyo n'indwara zo mu kanwa. Mugize impamvu ituma muhindura gahunda, mwaduhamagara kuri {clinic_phone}.

English:
Dear {full_name}, your next appointment with {dentist_name} is scheduled on {appointment_date} at {appointment_time} at {clinic_name}.

Thank you for choosing our dental and oral health services. If you need to reschedule, please call us on {clinic_phone}."""


THANK_YOU_AFTER_SERVICE = """Kinyarwanda:
Ncuti {full_name}, mwakoze guhitamo serivisi z'ishami ryita ku menyo n'indwara zo mu kanwa muri {clinic_name}. Mwitaweho na {dentist_name}. Ubuzima bwanyu ni intego yacu. Murakoze cyane.

Mugize ikibazo cyangwa mukeneye ubujyanama mwaduhamagara kuri {clinic_phone}.

English:
Dear {full_name}, thank you for choosing dental and oral health services at {clinic_name}. You were cared for by {dentist_name}. Your health is our priority. Thank you very much.

If you have any concern or need advice, please call us on {clinic_phone}."""


APPOINTMENT_CONFIRMED = """Kinyarwanda:
Ncuti {full_name}, umunsi mwasabye wo kubonana na muganga {dentist_name} kuwa {appointment_date} saa {appointment_time}, wemejwe.

Murakoze guhitamo serivisi z'ishami ryita ku buzima bw'amenyo n'indwara zo mu kanwa muri {clinic_name}.

Mugize impamvu ituma muhindura gahunda, mwaduhamagara kuri {clinic_phone}.

English:
Dear {full_name}, your requested appointment with {dentist_name} on {appointment_date} at {appointment_time} has been confirmed.

Thank you for choosing dental and oral health services at {clinic_name}.

If you need to reschedule, please call us on {clinic_phone}."""


def patient_welcome_message(patient, dentist_name="our dental team"):
    return PATIENT_WELCOME.format(
        full_name=patient.user.full_name or patient.user.phone,
        dentist_name=dentist_name,
        clinic_name=settings.CLINIC_NAME,
    )


def appointment_message(template, appointment):
    return template.format(
        full_name=appointment.patient.user.full_name or appointment.patient.user.phone,
        dentist_name=str(appointment.dentist),
        appointment_date=appointment.appointment_date.strftime("%Y-%m-%d"),
        appointment_time=appointment.appointment_time.strftime("%H:%M"),
        clinic_name=settings.CLINIC_NAME,
        clinic_phone=settings.CLINIC_PHONE,
    )
