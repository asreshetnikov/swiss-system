"""
Standings calculation — pure function over closed round data.
"""
from __future__ import annotations

import functools
from collections import defaultdict
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
    2. Configured tiebreak_order (buchholz, wins, head_to_head)
    3. seed ASC (final fallback)
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

    # opponents_map[pid] = list of opponent IDs (byes excluded)
    opponents_map: dict[int, list[int]] = defaultdict(list)
    # h2h_scores[pid][opp_id] = points scored against opp_id
    h2h_scores: dict[int, dict[int, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

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
                        h2h_scores[w_id][b_id] += Decimal("1")
                if b_id and b_id in scores:
                    scores[b_id]["losses"] += 1
                    scores[b_id]["games_played"] += 1

            elif result == Pairing.Result.BLACK_WIN:
                if b_id and b_id in scores:
                    scores[b_id]["points"] += Decimal("1")
                    scores[b_id]["wins"] += 1
                    scores[b_id]["games_played"] += 1
                    if w_id and w_id in scores:
                        h2h_scores[b_id][w_id] += Decimal("1")
                if w_id and w_id in scores:
                    scores[w_id]["losses"] += 1
                    scores[w_id]["games_played"] += 1

            elif result == Pairing.Result.DRAW:
                if w_id and w_id in scores:
                    scores[w_id]["points"] += Decimal("0.5")
                    scores[w_id]["draws"] += 1
                    scores[w_id]["games_played"] += 1
                    if b_id and b_id in scores:
                        h2h_scores[w_id][b_id] += Decimal("0.5")
                if b_id and b_id in scores:
                    scores[b_id]["points"] += Decimal("0.5")
                    scores[b_id]["draws"] += 1
                    scores[b_id]["games_played"] += 1
                    if w_id and w_id in scores:
                        h2h_scores[b_id][w_id] += Decimal("0.5")

            elif result == Pairing.Result.FORFEIT:
                if w_id and w_id in scores:
                    scores[w_id]["games_played"] += 1
                if b_id and b_id in scores:
                    scores[b_id]["games_played"] += 1

            # Track opponents for Buchholz (only real games, not byes)
            if w_id and w_id in scores and b_id and b_id in scores:
                opponents_map[w_id].append(b_id)
                opponents_map[b_id].append(w_id)

    # Compute Buchholz: sum of opponents' points
    buchholz: dict[int, float] = {}
    for pid in scores:
        buchholz[pid] = sum(
            float(scores[opp_id]["points"])
            for opp_id in opponents_map[pid]
            if opp_id in scores
        )

    tiebreak_order = tournament.tiebreak_order or []

    def compare(a: dict, b: dict) -> int:
        pts_a = float(a["points"])
        pts_b = float(b["points"])
        if pts_b != pts_a:
            return 1 if pts_b > pts_a else -1
        for tb in tiebreak_order:
            if tb == "buchholz":
                diff = buchholz[b["participant_id"]] - buchholz[a["participant_id"]]
            elif tb == "wins":
                diff = b["wins"] - a["wins"]
            elif tb == "head_to_head":
                diff = float(
                    h2h_scores[b["participant_id"]].get(a["participant_id"], Decimal("0"))
                    - h2h_scores[a["participant_id"]].get(b["participant_id"], Decimal("0"))
                )
            else:
                diff = 0
            if diff != 0:
                return 1 if diff > 0 else -1
        # Final fallback: seed ASC
        seed_a = a["seed"] or 9999
        seed_b = b["seed"] or 9999
        return seed_a - seed_b

    ordered = sorted(scores.values(), key=functools.cmp_to_key(compare))

    # Assign rank and finalize types
    for i, row in enumerate(ordered, start=1):
        row["rank"] = i
        row["points"] = float(row["points"])
        row["buchholz"] = round(buchholz[row["participant_id"]], 1)

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
