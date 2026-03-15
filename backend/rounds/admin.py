from django.contrib import admin

from .models import Pairing, Round


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ("tournament", "number", "status", "created_at")
    list_filter = ("status",)


@admin.register(Pairing)
class PairingAdmin(admin.ModelAdmin):
    list_display = ("round", "board_number", "white", "black", "result", "is_bye")
    list_filter = ("result", "is_bye")
