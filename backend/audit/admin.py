from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("tournament", "actor", "action", "entity_type", "entity_id", "created_at")
    list_filter = ("action", "entity_type")
    readonly_fields = ("tournament", "actor", "action", "entity_type", "entity_id", "before", "after", "reason", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
