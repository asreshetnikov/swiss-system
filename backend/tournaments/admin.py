from django.contrib import admin

from .models import Tournament


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "status", "num_rounds", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    readonly_fields = ("slug", "created_at", "updated_at")
