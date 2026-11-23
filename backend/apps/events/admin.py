from django.contrib import admin

from apps.events.models import ChecklistItem, Event, Speaker


class ChecklistInline(admin.TabularInline):
    model = ChecklistItem
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "speaker", "starts_at", "status")
    list_filter = ("status",)
    inlines = [ChecklistInline]


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "topic")
