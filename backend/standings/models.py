from django.db import models


class StandingSnapshot(models.Model):
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="standing_snapshots",
    )
    round = models.ForeignKey(
        "rounds.Round",
        on_delete=models.CASCADE,
        related_name="standing_snapshots",
        null=True,
        blank=True,
    )
    # Ordered list of {participant_id, name, points, seed, wins, draws, losses, ...}
    data = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("tournament", "round")]

    def __str__(self):
        round_label = f"after round {self.round.number}" if self.round else "current"
        return f"Standings for {self.tournament} ({round_label})"
