from django import forms

from dental_system.upload_validation import validate_uploaded_attachment
from .models import DoctorConversation, DoctorMessage

_INPUT = (
    "width:100%;border:1.5px solid #e2e8f0;border-radius:12px;"
    "padding:11px 14px;font-size:14px;outline:none;box-sizing:border-box;"
    "transition:border-color .18s,box-shadow .18s;background:#fff;"
)
_FOCUS = (
    "onfocus=\"this.style.borderColor='#0B7A4B';this.style.boxShadow='0 0 0 3px rgba(11,122,75,.1)'\""
    " onblur=\"this.style.borderColor='#e2e8f0';this.style.boxShadow='none'\""
)


class AskDoctorForm(forms.Form):
    """Structured question form for patients."""
    CATEGORY_CHOICES = [
        ("", "Select a topic (optional)"),
        ("pain", "Tooth Pain or Sensitivity"),
        ("cosmetic", "Cosmetic Dentistry"),
        ("hygiene", "Oral Hygiene"),
        ("emergency", "Dental Emergency"),
        ("orthodontics", "Braces & Orthodontics"),
        ("implants", "Dental Implants"),
        ("pediatric", "Children's Dentistry"),
        ("insurance", "Insurance & Billing"),
        ("general", "General Question"),
        ("other", "Other"),
    ]

    subject = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            "placeholder": "What is your question about?",
            "style": _INPUT,
            "onfocus": "this.style.borderColor='#0B7A4B';this.style.boxShadow='0 0 0 3px rgba(11,122,75,.1)'",
            "onblur": "this.style.borderColor='#e2e8f0';this.style.boxShadow='none'",
        }),
    )
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            "style": _INPUT,
            "onfocus": "this.style.borderColor='#0B7A4B';this.style.boxShadow='0 0 0 3px rgba(11,122,75,.1)'",
            "onblur": "this.style.borderColor='#e2e8f0';this.style.boxShadow='none'",
        }),
    )
    message = forms.CharField(
        max_length=4000,
        widget=forms.Textarea(attrs={
            "rows": 6,
            "placeholder": "Describe your question or concern in detail…",
            "style": _INPUT + "resize:vertical;",
            "onfocus": "this.style.borderColor='#0B7A4B';this.style.boxShadow='0 0 0 3px rgba(11,122,75,.1)'",
            "onblur": "this.style.borderColor='#e2e8f0';this.style.boxShadow='none'",
            "maxlength": 4000,
        }),
    )
    attachment = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "style": _INPUT,
            "accept": "image/*,.pdf,.doc,.docx",
        }),
    )

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        validate_uploaded_attachment(attachment)
        return attachment


class SendMessageForm(forms.Form):
    """Simple message input used in the chat interface."""
    message = forms.CharField(
        max_length=4000,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Type your message…",
            "style": _INPUT + "resize:none;",
            "maxlength": 4000,
            "onfocus": "this.style.borderColor='#0B7A4B';this.style.boxShadow='0 0 0 3px rgba(11,122,75,.1)'",
            "onblur": "this.style.borderColor='#e2e8f0';this.style.boxShadow='none'",
        }),
    )
    attachment = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "style": _INPUT,
            "accept": "image/*,.pdf,.doc,.docx",
        }),
    )

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        validate_uploaded_attachment(attachment)
        return attachment
