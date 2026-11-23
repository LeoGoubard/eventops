from django.contrib import admin

from apps.sales.models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("event", "amount_cents", "refunded_cents", "currency", "paid_at")
    list_filter = ("currency",)
    readonly_fields = ("stripe_session_id", "stripe_payment_intent_id")
