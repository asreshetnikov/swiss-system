"""Unit tests for the Swiss pairing engine."""
import random
from decimal import Decimal

from pairing.engine import PlayerState, generate_pairings


def make_player(
    id: int,
    seed: int,
    points: float = 0.0,
    colors_history=None,
    opponents_history=None,
    bye_received: bool = False,
    status: str = "ACTIVE",
) -> PlayerState:
    return PlayerState(
        id=id,
        seed=seed,
        points=Decimal(str(points)),
        colors_history=colors_history or [],
        opponents_history=opponents_history or [],
        bye_received=bye_received,
        status=status,
    )


# ── Round 1 ──────────────────────────────────────────────────────────────────


class TestRound1Even:
    def test_basic_even(self):
        players = [make_player(i, i) for i in range(1, 9)]  # seeds 1-8
        pairs = generate_pairings(1, players)
        assert len(pairs) == 4
        # No byes
        assert all(not p.is_bye for p in pairs)

    def test_top_vs_bottom(self):
        """Seed 1 vs seed 5, seed 2 vs seed 6, etc."""
        players = [make_player(i, i) for i in range(1, 9)]
        pairs = generate_pairings(1, players)
        game_pairs = [p for p in pairs if not p.is_bye]
        ids = {frozenset([p.white_id, p.black_id]) for p in game_pairs}
        assert frozenset([1, 5]) in ids
        assert frozenset([2, 6]) in ids
        assert frozenset([3, 7]) in ids
        assert frozenset([4, 8]) in ids


class TestRound1Odd:
    def test_odd_gives_bye(self):
        players = [make_player(i, i) for i in range(1, 8)]  # 7 players
        pairs = generate_pairings(1, players)
        byes = [p for p in pairs if p.is_bye]
        games = [p for p in pairs if not p.is_bye]
        assert len(byes) == 1
        assert len(games) == 3

    def test_bye_goes_to_last_seed(self):
        """Last by seed (seed 7) gets the bye in round 1."""
        players = [make_player(i, i) for i in range(1, 8)]
        pairs = generate_pairings(1, players)
        bye_pair = next(p for p in pairs if p.is_bye)
        assert bye_pair.white_id == 7

    def test_top_vs_bottom_after_bye_removal(self):
        """After bye removal (seed 7), pairs should be 1v4, 2v5, 3v6."""
        players = [make_player(i, i) for i in range(1, 8)]
        pairs = generate_pairings(1, players)
        game_pairs = [p for p in pairs if not p.is_bye]
        ids = {frozenset([p.white_id, p.black_id]) for p in game_pairs}
        assert frozenset([1, 4]) in ids
        assert frozenset([2, 5]) in ids
        assert frozenset([3, 6]) in ids


# ── Round 2+ ─────────────────────────────────────────────────────────────────


class TestRound2Grouping:
    def test_score_groups(self):
        """After round 1: 1-0 scores paired together, 0-1 together."""
        # Simulate: seeds 1,2 won; seeds 3,4 lost
        players = [
            make_player(1, 1, points=1.0, opponents_history=[3]),
            make_player(2, 2, points=1.0, opponents_history=[4]),
            make_player(3, 3, points=0.0, opponents_history=[1]),
            make_player(4, 4, points=0.0, opponents_history=[2]),
        ]
        pairs = generate_pairings(2, players)
        games = [p for p in pairs if not p.is_bye]
        ids = {frozenset([p.white_id, p.black_id]) for p in games}
        # 1 vs 2, 3 vs 4
        assert frozenset([1, 2]) in ids
        assert frozenset([3, 4]) in ids

    def test_float_down(self):
        """Odd player in score group floats to next group."""
        # 3 players with 1 point, 1 with 0 — one must float down
        players = [
            make_player(1, 1, points=1.0, opponents_history=[4]),
            make_player(2, 2, points=1.0, opponents_history=[3]),
            make_player(3, 3, points=1.0, opponents_history=[2]),
            make_player(4, 4, points=0.0, opponents_history=[1]),
        ]
        pairs = generate_pairings(2, players)
        games = [p for p in pairs if not p.is_bye]
        # Should produce 2 pairs
        assert len(games) == 2


class TestNoRepeatConstraint:
    def test_no_repeat_opponents(self):
        """Players who already met should not be paired again if avoidable."""
        players = [
            make_player(1, 1, points=1.0, opponents_history=[2]),
            make_player(2, 2, points=1.0, opponents_history=[1]),
            make_player(3, 3, points=0.0, opponents_history=[4]),
            make_player(4, 4, points=0.0, opponents_history=[3]),
        ]
        pairs = generate_pairings(2, players)
        games = [p for p in pairs if not p.is_bye]
        # 1 should not meet 2 again; 3 should not meet 4 again
        pair_sets = {frozenset([p.white_id, p.black_id]) for p in games}
        assert frozenset([1, 2]) not in pair_sets
        assert frozenset([3, 4]) not in pair_sets

    def test_forced_repeat_when_unavoidable(self):
        """With only 2 players, repeat is unavoidable — should still produce a pair."""
        players = [
            make_player(1, 1, points=1.0, opponents_history=[2]),
            make_player(2, 2, points=0.0, opponents_history=[1]),
        ]
        pairs = generate_pairings(2, players)
        assert len(pairs) == 1
        assert not pairs[0].is_bye


# ── Bye assignment ────────────────────────────────────────────────────────────


class TestByeAssignment:
    def test_bye_to_last_seed_without_prior_bye(self):
        players = [
            make_player(1, 1, points=1.0),
            make_player(2, 2, points=0.5),
            make_player(3, 3, points=0.0),  # last, no prior bye
        ]
        pairs = generate_pairings(2, players)
        bye_pair = next(p for p in pairs if p.is_bye)
        assert bye_pair.white_id == 3

    def test_no_double_bye(self):
        """Player who already had bye should not get second bye if someone else is available."""
        players = [
            make_player(1, 1, points=1.5, bye_received=True),
            make_player(2, 2, points=1.0),
            make_player(3, 3, points=0.5),  # should get bye, not player 1
        ]
        pairs = generate_pairings(2, players)
        bye_pair = next(p for p in pairs if p.is_bye)
        assert bye_pair.white_id != 1

    def test_double_bye_forced_when_all_received(self):
        """If all players had bye, fall back to last by seed."""
        players = [
            make_player(1, 1, points=2.0, bye_received=True),
            make_player(2, 2, points=1.0, bye_received=True),
            make_player(3, 3, points=0.0, bye_received=True),
        ]
        pairs = generate_pairings(3, players)
        bye_pairs = [p for p in pairs if p.is_bye]
        assert len(bye_pairs) == 1
        # Falls back to last seed = 3
        assert bye_pairs[0].white_id == 3


# ── Withdrawn players ─────────────────────────────────────────────────────────


class TestWithdrawnExclusion:
    def test_withdrawn_excluded_from_pairings(self):
        players = [
            make_player(1, 1, points=1.0),
            make_player(2, 2, points=0.5, status="WITHDRAWN"),
            make_player(3, 3, points=0.0),
            make_player(4, 4, points=0.0),
        ]
        pairs = generate_pairings(2, players)
        all_ids = set()
        for p in pairs:
            if p.white_id:
                all_ids.add(p.white_id)
            if p.black_id:
                all_ids.add(p.black_id)
        assert 2 not in all_ids

    def test_withdrawn_does_not_get_bye(self):
        players = [
            make_player(1, 1),
            make_player(2, 2),
            make_player(3, 3, status="WITHDRAWN"),
        ]
        pairs = generate_pairings(1, players)
        # Should be 1 game + 0 byes (withdrawn excluded, 2 active = even)
        byes = [p for p in pairs if p.is_bye]
        games = [p for p in pairs if not p.is_bye]
        assert len(byes) == 0
        assert len(games) == 1


# ── Color assignment ──────────────────────────────────────────────────────────


class TestColorAssignment:
    def test_all_players_assigned_color(self):
        players = [make_player(i, i) for i in range(1, 5)]
        pairs = generate_pairings(1, players)
        for p in pairs:
            if not p.is_bye:
                assert p.white_id is not None
                assert p.black_id is not None
                assert p.white_id != p.black_id

    def test_deterministic_with_fixed_rng(self):
        """Same rng seed → same colors."""
        players = [make_player(i, i) for i in range(1, 9)]
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        pairs1 = generate_pairings(1, players, rng=rng1)
        pairs2 = generate_pairings(1, players, rng=rng2)
        for p1, p2 in zip(pairs1, pairs2):
            assert p1.white_id == p2.white_id
            assert p1.black_id == p2.black_id

    def test_colors_alternate(self):
        """Colors must alternate: if board 1 top is white, board 2 top is black, etc."""
        players = [make_player(i, i) for i in range(1, 9)]  # seeds 1-8
        # Run many times — alternation must always hold regardless of random start
        for seed in range(20):
            pairs = generate_pairings(1, players, rng=random.Random(seed))
            games = [p for p in pairs if not p.is_bye]
            # board i: top-half player id == i (seed 1..4), bottom-half == i+4
            top_is_white = [p.white_id <= 4 for p in games]
            for i in range(1, len(top_is_white)):
                assert top_is_white[i] != top_is_white[i - 1], (
                    f"seed={seed}: colors not alternating at board {i}"
                )

    def test_random_start_color(self):
        """Over many runs the first board gets both colors."""
        players = [make_player(i, i) for i in range(1, 9)]
        first_whites = set()
        for seed in range(40):
            pairs = generate_pairings(1, players, rng=random.Random(seed))
            games = [p for p in pairs if not p.is_bye]
            first_whites.add(games[0].white_id)
        # Should see both seed-1 (top) and seed-5 (bottom) as white on board 1
        assert 1 in first_whites
        assert 5 in first_whites
