from django.db import models


class Participant(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        DISQUALIFIED = "DISQUALIFIED", "Disqualified"

    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="participants",
    )
    name = models.CharField(max_length=200)
    rating = models.PositiveIntegerField(null=True, blank=True)
    seed = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["seed", "created_at"]
        unique_together = [("tournament", "seed")]

    def __str__(self):
        return f"{self.name} ({self.tournament})"
