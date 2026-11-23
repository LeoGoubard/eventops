from django.contrib import admin

from apps.accounts.models import Membership


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
