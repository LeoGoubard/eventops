from django.db import models

from apps.events.models import Event


class Sale(models.Model):
    """One paid Stripe Checkout Session, attributed to the event that generated it.

    No customer data is stored here: the buyer stays in Stripe, EventOps only keeps
    what it needs to report revenue per event and per speaker.
    """

    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="sales")
    stripe_session_id = models.CharField(max_length=255, unique=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)
    amount_cents = models.PositiveIntegerField()
    refunded_cents = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3)
    paid_at = models.DateTimeField()

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self) -> str:
        return f"{self.event}: {self.amount_cents / 100:.2f} {self.currency.upper()}"
