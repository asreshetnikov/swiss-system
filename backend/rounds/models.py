from django.db import models


class Round(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        CLOSED = "CLOSED", "Closed"

    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="rounds",
    )
    number = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["number"]
        unique_together = [("tournament", "number")]

    def __str__(self):
        return f"Round {self.number} of {self.tournament}"


class Pairing(models.Model):
    class Result(models.TextChoices):
        PENDING = "PENDING", "Pending"
        WHITE_WIN = "WHITE_WIN", "White Win"
        BLACK_WIN = "BLACK_WIN", "Black Win"
        DRAW = "DRAW", "Draw"
        BYE = "BYE", "Bye"
        FORFEIT = "FORFEIT", "Forfeit"

    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="pairings")
    board_number = models.PositiveSmallIntegerField()
    white = models.ForeignKey(
        "participants.Participant",
        on_delete=models.CASCADE,
        related_name="pairings_as_white",
        null=True,
        blank=True,
    )
    black = models.ForeignKey(
        "participants.Participant",
        on_delete=models.CASCADE,
        related_name="pairings_as_black",
        null=True,
        blank=True,
    )
    result = models.CharField(max_length=10, choices=Result.choices, default=Result.PENDING)
    is_bye = models.BooleanField(default=False)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["board_number"]
        unique_together = [("round", "board_number")]

    def __str__(self):
        if self.is_bye:
            return f"Round {self.round.number} Board {self.board_number}: BYE"
        return f"Round {self.round.number} Board {self.board_number}: {self.white} vs {self.black}"
