from django.db import models


class Contact(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    marketing_consent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email
