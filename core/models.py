# core/models.py

from django.db import models


class ContactMessage(models.Model):
    """Stores every contact form submission for admin review."""

    SUBJECT_CHOICES = [
        ("general",     "General Inquiry"),
        ("sales",       "Sales & Pricing"),
        ("support",     "Technical Support"),
        ("feature",     "Feature Request"),
        ("bug",         "Report a Bug"),
        ("partnership", "Partnership Opportunity"),
    ]

    name         = models.CharField(max_length=255)
    email        = models.EmailField()
    phone        = models.CharField(max_length=30, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    subject      = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    message      = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read      = models.BooleanField(default=False)

    class Meta:
        ordering            = ["-submitted_at"]
        verbose_name        = "Contact Message"
        verbose_name_plural = "Contact Messages"

    def __str__(self):
        return f"{self.name} — {self.get_subject_display()} ({self.submitted_at:%d %b %Y})"