"""
Swiss pairing engine — pure functions, no ORM dependencies.

All inputs/outputs are plain Python data structures.
"""
from __future__ import annotations

import random as _random
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class PlayerState:
    id: int
    seed: int
    points: Decimal
    colors_history: list[str]  # 'W' or 'B' per past round
    opponents_history: list[int]  # participant IDs
    bye_received: bool
    status: str  # 'ACTIVE', 'WITHDRAWN', 'DISQUALIFIED'


@dataclass
class Pair:
    white_id: Optional[int]  # None means BYE
    black_id: Optional[int]  # None means BYE
    is_bye: bool = False


def _active(players: list[PlayerState]) -> list[PlayerState]:
    return [p for p in players if p.status == "ACTIVE"]


def _cd(player: PlayerState) -> int:
    """Signed color difference: whites played minus blacks played."""
    return player.colors_history.count("W") - player.colors_history.count("B")


def _color_due(player: PlayerState) -> str:
    """Return the color this player is due next ('W' or 'B').

    CD = whites - blacks:
      CD > 0 → due black
      CD < 0 → due white
      CD = 0 → prefer opposite of last game; if no history, prefer white
    """
    whites = player.colors_history.count("W")
    blacks = player.colors_history.count("B")
    cd = whites - blacks
    if cd > 0:
        return "B"
    if cd < 0:
        return "W"
    if player.colors_history:
        return "B" if player.colors_history[-1] == "W" else "W"
    return "W"


def _assign_colors(p1: PlayerState, p2: PlayerState) -> tuple[int, int]:
    """Return (white_id, black_id) per FIDE Dutch System rules.

    p1 is assumed to be the higher-ranked player (better score / lower seed).

    Complementary preferences: each player gets their due color.
    Same preference (color conflict): the player with higher |CD| gets their
    due color; if |CD| is equal, p1 (higher-ranked) gets their due color.
    """
    due1 = _color_due(p1)
    due2 = _color_due(p2)

    if due1 != due2:
        # Complementary — each gets what they're due
        white, black = (p1, p2) if due1 == "W" else (p2, p1)
        return white.id, black.id

    # Conflict: both due the same color.
    # Determine who wins: higher |CD| takes priority; ties go to p1 (higher-ranked).
    winner, loser = (p1, p2) if abs(_cd(p1)) >= abs(_cd(p2)) else (p2, p1)

    # Winner gets their due color (same for both since they're in conflict)
    if due1 == "W":
        return winner.id, loser.id
    else:
        return loser.id, winner.id


def _assign_bye(players: list[PlayerState]) -> Optional[PlayerState]:
    """Return the player who should receive a bye.

    Assigns bye to the lowest-ranked player who has not yet received a bye.
    Lowest-ranked = fewest points first; within equal points, worst seed
    (highest seed number) first — matching the bottom of the standings table.
    Falls back to the same ordering when everyone has already had a bye.
    """
    by_standing = sorted(players, key=lambda p: (p.points, -p.seed))
    candidates = [p for p in by_standing if not p.bye_received]
    if not candidates:
        candidates = by_standing
    return candidates[0] if candidates else None


def generate_pairings(
    round_number: int,
    players: list[PlayerState],
    rng: Optional[_random.Random] = None,
) -> list[Pair]:
    """
    Generate pairings for the given round.

    round_number: 1-based round index
    players: all participants (active and non-active)
    rng: optional Random instance for reproducible results (used in tests)

    Returns list of Pair objects. Bye pairs have is_bye=True and one side None.
    """
    active = _active(players)
    if not active:
        return []

    pairs: list[Pair] = []
    bye_player: Optional[PlayerState] = None

    if len(active) % 2 == 1:
        bye_player = _assign_bye(active)
        active = [p for p in active if p.id != bye_player.id]
        pairs.append(Pair(white_id=bye_player.id, black_id=None, is_bye=True))

    if round_number == 1:
        _rng = rng or _random.Random()
        top_starts_white: bool = _rng.choice([True, False])
        pairs += _round1_pairings(active, top_starts_white)
    else:
        pairs += _swiss_pairings(active)

    return pairs


def _round1_pairings(players: list[PlayerState], top_starts_white: bool) -> list[Pair]:
    """
    Top-half vs bottom-half by seed.
    Colors alternate pair-by-pair; the first pair's color is controlled by
    top_starts_white (chosen randomly by the caller).
    """
    sorted_players = sorted(players, key=lambda p: p.seed)
    n = len(sorted_players)
    half = n // 2
    top = sorted_players[:half]
    bottom = sorted_players[half:]
    result = []
    for i, (p1, p2) in enumerate(zip(top, bottom)):
        # Alternate: even board → use top_starts_white, odd board → flip
        if top_starts_white if i % 2 == 0 else not top_starts_white:
            result.append(Pair(white_id=p1.id, black_id=p2.id))
        else:
            result.append(Pair(white_id=p2.id, black_id=p1.id))
    return result


def _choose_floater(
    candidates: list[PlayerState],
    next_players: list[PlayerState],
) -> PlayerState:
    """
    Choose which player floats down from the current score group to the next.

    Iterates candidates from worst-ranked to best-ranked (reverse of the
    sorted order: highest seed / lowest |CD| first).

    Two criteria, applied in order:
    1. Avoid sending a player who has already played *all* players in the next
       group — that would force a repeat match in the receiving group.
    2. Prefer a player whose color_due complements the dominant color need of
       next_players, reducing color collisions in the next group.

    Falls back to the worst-ranked candidate when no preferred choice exists.
    """
    def _has_fresh_opponent(candidate: PlayerState) -> bool:
        """True if the candidate has at least one unplayed opponent in next_players."""
        return any(p.id not in candidate.opponents_history for p in next_players)

    if next_players:
        due_counts: dict[str, int] = {"W": 0, "B": 0}
        for p in next_players:
            due_counts[_color_due(p)] += 1

        if due_counts["B"] != due_counts["W"]:
            # Float someone whose due color complements the next group's majority,
            # but only if they haven't already played everyone down there.
            preferred_due = "W" if due_counts["B"] > due_counts["W"] else "B"
            for candidate in reversed(candidates):
                if _color_due(candidate) == preferred_due and _has_fresh_opponent(candidate):
                    return candidate

    # No color-preferred candidate found — pick worst-ranked that avoids a forced repeat
    for candidate in reversed(candidates):
        if _has_fresh_opponent(candidate):
            return candidate

    # All candidates have played everyone in the next group — unavoidable repeat;
    # return worst-ranked as last resort.
    return candidates[-1]


def _swiss_pairings(players: list[PlayerState]) -> list[Pair]:
    """
    Round 2+: group by points (desc), pair within groups.
    Float odd players down to next group.
    Avoid repeat opponents.
    """
    # Sort by (points DESC, seed ASC)
    sorted_players = sorted(players, key=lambda p: (-p.points, p.seed))

    # Build score groups
    groups: dict[Decimal, list[PlayerState]] = {}
    for p in sorted_players:
        groups.setdefault(p.points, []).append(p)

    score_keys = sorted(groups.keys(), reverse=True)

    # Process groups with floaters
    unpaired: list[PlayerState] = []
    result: list[Pair] = []

    for i, score in enumerate(score_keys):
        # Within each score group: higher |CD| first, then seed ascending.
        # This ensures players with greater color imbalance get first pick of
        # complementary-color opponents.
        current = sorted(groups[score], key=lambda p: (-abs(_cd(p)), p.seed))
        group = unpaired + current
        unpaired = []

        # If group has odd count, pre-select the down-floater using color-aware
        # logic. Native players (current) are tried first because they are at the
        # tail of `group` in reversed order — only if none of them can provide a
        # fresh opponent in the next group does the algorithm allow a player who
        # already floated down from above to cascade further.
        pre_floater: Optional[PlayerState] = None
        if len(group) % 2 == 1:
            next_score_players = (
                groups[score_keys[i + 1]] if i + 1 < len(score_keys) else []
            )
            pre_floater = _choose_floater(group, next_score_players)
            group = [p for p in group if p.id != pre_floater.id]

        group_pairs, leftover = _pair_group(group)
        result.extend(group_pairs)

        if pre_floater is not None:
            unpaired.append(pre_floater)
        unpaired.extend(leftover)

    # Handle any remaining — force pair even if repeat (last resort)
    if len(unpaired) >= 2:
        while len(unpaired) >= 2:
            p1 = unpaired.pop(0)
            p2 = unpaired.pop(0)
            white_id, black_id = _assign_colors(p1, p2)
            result.append(Pair(white_id=white_id, black_id=black_id))

    return result


def _pair_group(players: list[PlayerState]) -> tuple[list[Pair], list[PlayerState]]:
    """
    Pair players in the group per FIDE Dutch System color rules.

    Two-pass search for each player:
      Pass 1 — complementary color due + no repeat opponent (ideal).
      Pass 2 — any non-repeat opponent (color violation accepted).

    Players with no valid non-repeat opponent float to the next score group.
    Returns (pairs, unpaired_floaters).
    """
    remaining = list(players)
    pairs: list[Pair] = []
    floaters: list[PlayerState] = []

    while remaining:
        p1 = remaining.pop(0)
        due1 = _color_due(p1)
        paired = False

        # Pass 1: complementary color + no repeat
        for i, p2 in enumerate(remaining):
            if p2.id not in p1.opponents_history and _color_due(p2) != due1:
                remaining.pop(i)
                white_id, black_id = _assign_colors(p1, p2)
                pairs.append(Pair(white_id=white_id, black_id=black_id))
                paired = True
                break

        if not paired:
            # Pass 2: any non-repeat (color violation accepted)
            for i, p2 in enumerate(remaining):
                if p2.id not in p1.opponents_history:
                    remaining.pop(i)
                    white_id, black_id = _assign_colors(p1, p2)
                    pairs.append(Pair(white_id=white_id, black_id=black_id))
                    paired = True
                    break

        if not paired:
            floaters.append(p1)

    floaters.extend(remaining)
    return pairs, floaters
