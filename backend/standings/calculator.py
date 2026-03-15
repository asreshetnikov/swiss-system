"""
Standings calculation — pure function over closed round data.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from rounds.models import Pairing, Round
from tournaments.models import Tournament

from .models import StandingSnapshot


def calculate_standings(tournament: Tournament) -> list[dict[str, Any]]:
    """
    Calculate current standings for a tournament.

    Returns an ordered list of participant records sorted by:
    1. points DESC
    2. seed ASC (lower seed = better tiebreak in MVP)
    """
    participants = list(tournament.participants.all())
    closed_rounds = list(
        tournament.rounds.filter(status=Round.Status.CLOSED).order_by("number")
    )

    # Initialize score tracking
    scores: dict[int, dict[str, Any]] = {}
    for p in participants:
        scores[p.id] = {
            "participant_id": p.id,
            "name": p.name,
            "rating": p.rating,
            "seed": p.seed,
            "points": Decimal("0"),
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "byes": 0,
            "games_played": 0,
        }

    bye_points = tournament.bye_points

    for round_obj in closed_rounds:
        for pairing in round_obj.pairings.all():
            result = pairing.result

            if pairing.is_bye and pairing.white_id:
                pid = pairing.white_id
                if pid in scores:
                    scores[pid]["points"] += Decimal(str(bye_points))
                    scores[pid]["byes"] += 1
                continue

            if result == Pairing.Result.PENDING:
                continue

            w_id = pairing.white_id
            b_id = pairing.black_id

            if result == Pairing.Result.WHITE_WIN:
                if w_id and w_id in scores:
                    scores[w_id]["points"] += Decimal("1")
                    scores[w_id]["wins"] += 1
                    scores[w_id]["games_played"] += 1
                if b_id and b_id in scores:
                    scores[b_id]["losses"] += 1
                    scores[b_id]["games_played"] += 1

            elif result == Pairing.Result.BLACK_WIN:
                if b_id and b_id in scores:
                    scores[b_id]["points"] += Decimal("1")
                    scores[b_id]["wins"] += 1
                    scores[b_id]["games_played"] += 1
                if w_id and w_id in scores:
                    scores[w_id]["losses"] += 1
                    scores[w_id]["games_played"] += 1

            elif result == Pairing.Result.DRAW:
                if w_id and w_id in scores:
                    scores[w_id]["points"] += Decimal("0.5")
                    scores[w_id]["draws"] += 1
                    scores[w_id]["games_played"] += 1
                if b_id and b_id in scores:
                    scores[b_id]["points"] += Decimal("0.5")
                    scores[b_id]["draws"] += 1
                    scores[b_id]["games_played"] += 1

            elif result == Pairing.Result.FORFEIT:
                # Both get 0 for a forfeit
                if w_id and w_id in scores:
                    scores[w_id]["games_played"] += 1
                if b_id and b_id in scores:
                    scores[b_id]["games_played"] += 1

    # Sort by points DESC, then seed ASC
    ordered = sorted(
        scores.values(),
        key=lambda r: (-float(r["points"]), r["seed"] or 9999),
    )

    # Assign rank
    for i, row in enumerate(ordered, start=1):
        row["rank"] = i
        row["points"] = float(row["points"])

    return ordered


def save_snapshot(tournament: Tournament, round_obj: Round) -> StandingSnapshot:
    """Calculate standings and save a snapshot after closing a round."""
    data = calculate_standings(tournament)
    snapshot, _ = StandingSnapshot.objects.update_or_create(
        tournament=tournament,
        round=round_obj,
        defaults={"data": data},
    )
    return snapshot
