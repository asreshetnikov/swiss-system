from django.contrib import admin

from .models import Participant


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("name", "tournament", "rating", "seed", "status")
    list_filter = ("status", "tournament")
    search_fields = ("name",)
