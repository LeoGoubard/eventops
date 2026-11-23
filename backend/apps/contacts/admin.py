from django.contrib import admin

from apps.contacts.models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "marketing_consent", "created_at")
    search_fields = ("email", "first_name")
