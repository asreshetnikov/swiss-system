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


def _color_preference(player: PlayerState) -> str:
    """Return preferred next color ('W' or 'B') based on history."""
    whites = player.colors_history.count("W")
    blacks = player.colors_history.count("B")
    if whites > blacks:
        return "B"
    if blacks > whites:
        return "W"
    # Equal — prefer opposite of last
    if player.colors_history:
        return "B" if player.colors_history[-1] == "W" else "W"
    return "W"


def _assign_colors(p1: PlayerState, p2: PlayerState) -> tuple[int, int]:
    """Return (white_id, black_id)."""
    pref1 = _color_preference(p1)
    pref2 = _color_preference(p2)
    if pref1 == "W" and pref2 != "W":
        return p1.id, p2.id
    if pref2 == "W" and pref1 != "W":
        return p2.id, p1.id
    # Both same preference — give white to higher seed (lower number = better seed)
    if p1.seed < p2.seed:
        return p1.id, p2.id
    return p2.id, p1.id


def _assign_bye(players: list[PlayerState]) -> Optional[PlayerState]:
    """Return the player who should receive a bye (last by seed without prior bye)."""
    candidates = [p for p in reversed(sorted(players, key=lambda x: x.seed)) if not p.bye_received]
    if not candidates:
        # Everyone has had a bye — fall back to last by seed overall
        candidates = list(reversed(sorted(players, key=lambda x: x.seed)))
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

    for score in score_keys:
        group = unpaired + groups[score]
        unpaired = []

        # Try to pair within the group
        group_pairs, leftover = _pair_group(group)
        result.extend(group_pairs)
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
    Greedily pair players in the group, avoiding repeat opponents.
    Players who cannot be paired without a repeat float to the next group.
    Returns (pairs, unpaired_floaters).
    """
    remaining = list(players)
    pairs: list[Pair] = []
    floaters: list[PlayerState] = []

    while remaining:
        p1 = remaining.pop(0)
        paired = False
        for i, p2 in enumerate(remaining):
            if p2.id not in p1.opponents_history:
                remaining.pop(i)
                white_id, black_id = _assign_colors(p1, p2)
                pairs.append(Pair(white_id=white_id, black_id=black_id))
                paired = True
                break
        if not paired:
            # No valid (non-repeat) opponent found — float this player down
            floaters.append(p1)

    # Any single leftover (odd group) also floats
    floaters.extend(remaining)
    return pairs, floaters
