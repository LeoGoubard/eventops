from django.db import models


class Speaker(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    topic = models.CharField(max_length=300, blank=True)

    def __str__(self) -> str:
        return self.name


class EventStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    LIVE = "live", "Live"
    DONE = "done", "Done"


class Event(models.Model):
    title = models.CharField(max_length=300)
    speaker = models.ForeignKey(Speaker, on_delete=models.PROTECT, related_name="events")
    starts_at = models.DateTimeField(help_text="Stored in UTC, displayed in the viewer's timezone.")
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=20, choices=EventStatus.choices, default=EventStatus.DRAFT)
    join_url = models.URLField(blank=True)
    offer_url = models.URLField(blank=True, help_text="Sales page sent with the replay.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]

    def __str__(self) -> str:
        return self.title


class ChecklistItem(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="checklist")
    code = models.CharField(max_length=50)
    label = models.CharField(max_length=300)
    done = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["event", "code"], name="unique_checklist_code_per_event")
        ]

    def __str__(self) -> str:
        return f"{self.event}: {self.label}"
