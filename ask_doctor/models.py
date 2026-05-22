from django.conf import settings
from django.db import models


class DoctorConversation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PENDING = "pending", "Pending"
        ANSWERED = "answered", "Answered"
        CLOSED = "closed", "Closed"

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_conversations",
    )
    assigned_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_conversations",
    )
    subject = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"#{self.pk} — {self.patient.full_name}"

    @property
    def display_subject(self):
        if self.subject:
            return self.subject
        first = self.messages.order_by("created_at").first()
        if first:
            return first.message[:80]
        return f"Conversation #{self.pk}"

    @property
    def unread_for_staff(self):
        return self.messages.filter(
            is_read=False,
            sender__role="PATIENT",
        ).count()

    @property
    def unread_for_patient(self):
        return self.messages.filter(
            is_read=False,
        ).exclude(sender__role="PATIENT").count()


class DoctorMessage(models.Model):
    conversation = models.ForeignKey(
        DoctorConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_messages",
    )
    message = models.TextField(max_length=4000)
    attachment = models.FileField(
        upload_to="ask_doctor/attachments/",
        blank=True,
        null=True,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Msg #{self.pk} by {self.sender.full_name} in conv #{self.conversation_id}"

    @property
    def is_from_staff(self):
        return self.sender.role in ("ADMIN", "DENTIST")
