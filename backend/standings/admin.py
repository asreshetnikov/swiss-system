from django.contrib import admin

from .models import StandingSnapshot


@admin.register(StandingSnapshot)
class StandingSnapshotAdmin(admin.ModelAdmin):
    list_display = ("tournament", "round", "created_at")
    readonly_fields = ("created_at",)
