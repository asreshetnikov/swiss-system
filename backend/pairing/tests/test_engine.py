"""Unit tests for the Swiss pairing engine."""
import math
import random
from decimal import Decimal

import pytest

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


class TestFloaterSelection:
    def test_floater_chosen_for_color_compatibility(self):
        """When score group is odd, float the player whose color complements the next group."""
        # 1-point group (3 players, odd):
        #   p1 seed=1 due B (CD=+2), p2 seed=2 due W (CD=-2), p3 seed=3 due B (CD=+2)
        # 0-point group (5 players, all due B):
        #   next group is B-heavy → ideal floater is someone due W → p2
        #
        # Without color-aware logic the worst-ranked player (p3, seed=3, due B)
        # would float, causing an extra color collision in the 0-point group.
        # With color-aware logic p2 (due W, seed=2) floats instead.
        players = [
            make_player(1, 1, points=1.0, colors_history=["W", "W"], opponents_history=[5]),
            make_player(2, 2, points=1.0, colors_history=["B", "B"], opponents_history=[6]),
            make_player(3, 3, points=1.0, colors_history=["W", "W"], opponents_history=[7]),
            make_player(4, 4, points=0.0, colors_history=["W", "W"], opponents_history=[8]),
            make_player(5, 5, points=0.0, colors_history=["W"], opponents_history=[1]),
            make_player(6, 6, points=0.0, colors_history=["W"], opponents_history=[2]),
            make_player(7, 7, points=0.0, colors_history=["W"], opponents_history=[3]),
            make_player(8, 8, points=0.0, colors_history=["W"], opponents_history=[4]),
        ]
        pairs = generate_pairings(3, players)
        pair_sets = {frozenset([p.white_id, p.black_id]) for p in pairs if not p.is_bye}

        # p1 and p3 remain in the 1-point group and pair with each other
        assert frozenset([1, 3]) in pair_sets

        # p2 floated to the 0-point group — not paired with p1 or p3
        assert frozenset([1, 2]) not in pair_sets
        assert frozenset([2, 3]) not in pair_sets


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

    def test_floater_does_not_repeat_sole_player_in_next_group(self):
        """
        When a score group is odd and must send a floater down, the floater
        must not be a player who has already played everyone in the receiving
        group — that would force a repeat.

        Setup (round 3):
          Group 2.0 : p1  (solo → floats to 1.0 group)
          Group 1.0 : p2 (hasn't played p4), p3 (has played p4)
          Group 0.0 : p4

        Without the fix, p3 would be chosen as floater because its color_due
        complements p4's, resulting in a p3–p4 repeat.
        With the fix, p2 is chosen instead.
        """
        p1 = make_player(1, 1, points=2.0, colors_history=["W", "B"], opponents_history=[10, 11])
        p2 = make_player(2, 2, points=1.0, colors_history=["W", "B"], opponents_history=[10, 11])
        # p3 has already played p4
        p3 = make_player(3, 3, points=1.0, colors_history=["B", "W"], opponents_history=[4, 11])
        p4 = make_player(4, 4, points=0.0, colors_history=["W", "B"], opponents_history=[3, 11])

        pairs = generate_pairings(3, [p1, p2, p3, p4], rng=random.Random(42))
        games = [p for p in pairs if not p.is_bye]

        pair_sets = {frozenset([p.white_id, p.black_id]) for p in games}
        assert frozenset([3, 4]) not in pair_sets, "p3 and p4 must not be paired again"


# ── Bye assignment ────────────────────────────────────────────────────────────


class TestByeAssignment:
    def test_bye_to_last_in_standings(self):
        """Bye goes to the player last in standings: fewest points, then worst seed."""
        players = [
            make_player(1, 1, points=1.0),
            make_player(2, 2, points=0.5),
            make_player(3, 3, points=0.0),  # last in standings
        ]
        pairs = generate_pairings(2, players)
        bye_pair = next(p for p in pairs if p.is_bye)
        assert bye_pair.white_id == 3

    def test_bye_by_points_not_seed(self):
        """Bye goes to the player with fewest points even if their seed is better."""
        # p1 has worst seed (3) but 1 point; p3 has best seed (1) but 0 points.
        # Bye must go to p3 (last in standings), not p1 (last by seed).
        players = [
            make_player(1, 3, points=1.0),  # worst seed, but leads on points
            make_player(2, 2, points=0.5),
            make_player(3, 1, points=0.0),  # best seed, but last in standings
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
        """If all players had bye, fall back to last in standings."""
        players = [
            make_player(1, 1, points=2.0, bye_received=True),
            make_player(2, 2, points=1.0, bye_received=True),
            make_player(3, 3, points=0.0, bye_received=True),
        ]
        pairs = generate_pairings(3, players)
        bye_pairs = [p for p in pairs if p.is_bye]
        assert len(bye_pairs) == 1
        assert bye_pairs[0].white_id == 3  # last in standings


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


# ── FIDE color assignment ─────────────────────────────────────────────────────


class TestFIDEColorAssignment:
    def test_complementary_each_gets_due(self):
        """Player due white gets white when paired with player due black."""
        # p1: played B → due W (CD = -1)
        # p2: played W → due B (CD = +1)
        players = [
            make_player(1, 1, points=1.0, colors_history=["B"], opponents_history=[3]),
            make_player(2, 2, points=1.0, colors_history=["W"], opponents_history=[4]),
            make_player(3, 3, points=0.0, colors_history=["W"], opponents_history=[1]),
            make_player(4, 4, points=0.0, colors_history=["B"], opponents_history=[2]),
        ]
        pairs = generate_pairings(2, players)
        games = [p for p in pairs if not p.is_bye]
        pair_12 = next(p for p in games if {p.white_id, p.black_id} == {1, 2})
        assert pair_12.white_id == 1  # due white
        assert pair_12.black_id == 2  # due black

    def test_conflict_higher_cd_wins(self):
        """Player with higher |CD| gets their preferred color."""
        # p1: played W,B,W → CD=+1 → due B (mild)
        # p2: played W,W,W → CD=+3 → due B (absolute, stronger)
        # p2 has stronger need → p2 gets black; p1 gets white (violation)
        players = [
            make_player(1, 1, points=3.0, colors_history=["W", "B", "W"], opponents_history=[5, 6, 7]),
            make_player(2, 2, points=3.0, colors_history=["W", "W", "W"], opponents_history=[5, 6, 8]),
            make_player(5, 5, points=0.0, opponents_history=[1, 2]),
            make_player(6, 6, points=0.0, opponents_history=[1, 2]),
            make_player(7, 7, points=0.0, opponents_history=[1]),
            make_player(8, 8, points=0.0, opponents_history=[2]),
        ]
        pairs = generate_pairings(4, players)
        games = [p for p in pairs if not p.is_bye]
        pair_12 = next(p for p in games if {p.white_id, p.black_id} == {1, 2})
        assert pair_12.black_id == 2  # stronger need wins black
        assert pair_12.white_id == 1

    def test_conflict_equal_cd_higher_ranked_wins(self):
        """When |CD| is equal, higher-ranked player (better seed) gets their due color."""
        # Both played W,W → CD=+2 → both due black
        # p1 (seed 1) is higher-ranked → gets black; p2 gets white (violation)
        players = [
            make_player(1, 1, points=2.0, colors_history=["W", "W"], opponents_history=[3, 4]),
            make_player(2, 2, points=2.0, colors_history=["W", "W"], opponents_history=[3, 4]),
            make_player(3, 3, points=0.0, opponents_history=[1, 2]),
            make_player(4, 4, points=0.0, opponents_history=[1, 2]),
        ]
        pairs = generate_pairings(3, players)
        games = [p for p in pairs if not p.is_bye]
        pair_12 = next(p for p in games if {p.white_id, p.black_id} == {1, 2})
        assert pair_12.black_id == 1  # higher-ranked gets their due color (black)
        assert pair_12.white_id == 2

    def test_higher_cd_gets_complementary_over_better_seed(self):
        """Higher |CD| player gets complementary partner even if their seed is worse."""
        # CD=[1, 2, -1, 2] with seeds 1,2,3,4 — all same score.
        # Without |CD|-first sort: p1 (seed=1, CD=1) steals the only complementary
        #   partner (p3) from p4 (seed=4, CD=2), forcing p4 into a violation.
        # With |CD|-first sort: p2 (CD=2) and p4 (CD=2) are processed before
        #   p1 (CD=1), so both CD=2 players get black.
        players = [
            make_player(1, 1, points=1.0, colors_history=["B"], opponents_history=[5]),
            make_player(2, 2, points=1.0, colors_history=["W", "W"], opponents_history=[6]),
            make_player(3, 3, points=1.0, colors_history=["B", "B"], opponents_history=[7]),
            make_player(4, 4, points=1.0, colors_history=["W", "W"], opponents_history=[8]),
            make_player(5, 5, points=0.0, opponents_history=[1]),
            make_player(6, 6, points=0.0, opponents_history=[2]),
            make_player(7, 7, points=0.0, opponents_history=[3]),
            make_player(8, 8, points=0.0, opponents_history=[4]),
        ]
        pairs = generate_pairings(3, players)
        games = [p for p in pairs if not p.is_bye]
        # p2 (CD=+2) and p4 (CD=+2) must get black; p3 (CD=-2) gets white
        pair_24 = next((p for p in games if {p.white_id, p.black_id} == {2, 3}), None)
        pair_44 = next((p for p in games if {p.white_id, p.black_id} == {4, 3}), None)
        # One of them pairs with p3 (the only due-W player in top group)
        if pair_24:
            assert pair_24.black_id == 2
        if pair_44:
            assert pair_44.black_id == 4
        # The remaining CD=2 player wins their conflict and also gets black
        for p in games:
            if p.white_id in {2, 4} or p.black_id in {2, 4}:
                assert p.black_id in {2, 4}, f"CD=2 player {p.white_id} got white"

    def test_prefers_complementary_over_same_due(self):
        """Within a score group, prefers pairing with complementary-color player."""
        # p1 (due W), p2 (due W), p3 (due B) — all 1pt, no repeats among them
        # Without color preference: greedy pairs p1 vs p2 (first available)
        # With FIDE logic: p1 pairs with p3 (complementary), p2 floats
        players = [
            make_player(1, 1, points=1.0, colors_history=["B"], opponents_history=[4]),
            make_player(2, 2, points=1.0, colors_history=["B"], opponents_history=[5]),
            make_player(3, 3, points=1.0, colors_history=["W"], opponents_history=[6]),
            make_player(4, 4, points=0.0, colors_history=["W"], opponents_history=[1]),
            make_player(5, 5, points=0.0, colors_history=["W"], opponents_history=[2]),
            make_player(6, 6, points=0.0, colors_history=["B"], opponents_history=[3]),
        ]
        pairs = generate_pairings(2, players)
        games = [p for p in pairs if not p.is_bye]
        pair_sets = {frozenset([p.white_id, p.black_id]) for p in games}
        assert frozenset([1, 3]) in pair_sets  # complementary pairing
        assert frozenset([1, 2]) not in pair_sets  # same-due pairing avoided


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


# ── Simulated tournament ──────────────────────────────────────────────────────


def _simulate_tournament(num_players: int, num_rounds: int, rng_seed: int = 42) -> list[str]:
    """
    Run a full Swiss tournament simulation and return a list of repeat-pair descriptions.

    Rules: seed 1 = highest rated; lower seed always wins; no draws.
    Bye counts as a win for the bye recipient.
    """
    players = [make_player(id=i, seed=i) for i in range(1, num_players + 1)]
    seen_pairs: dict[frozenset, int] = {}
    repeats: list[str] = []
    rng = random.Random(rng_seed)

    for round_num in range(1, num_rounds + 1):
        pairings = generate_pairings(round_num, players, rng=rng)

        for pair in pairings:
            if pair.is_bye:
                p = next(x for x in players if x.id == pair.white_id)
                p.points += Decimal("1")
                p.bye_received = True
                continue

            key = frozenset([pair.white_id, pair.black_id])
            if key in seen_pairs:
                repeats.append(
                    f"Round {round_num}: players {pair.white_id} & {pair.black_id} "
                    f"already met in round {seen_pairs[key]}"
                )
            else:
                seen_pairs[key] = round_num

            white = next(x for x in players if x.id == pair.white_id)
            black = next(x for x in players if x.id == pair.black_id)

            if white.seed < black.seed:
                white.points += Decimal("1")
            else:
                black.points += Decimal("1")

            white.colors_history.append("W")
            black.colors_history.append("B")
            white.opponents_history.append(black.id)
            black.opponents_history.append(white.id)

    return repeats


class TestSimulatedTournament:
    """
    Full tournament simulations for 7–32 players.

    Rule: the higher-rated player (lower seed number) always wins; no draws.
    Number of rounds = ceil(log2(n)), the standard Swiss upper bound.

    The test verifies that the pairing engine never produces a repeated pair
    across the entire tournament.

    Note: the greedy (non-backtracking) algorithm can produce repeats when the
    lowest-ranked player exhausts all same-level opponents in very long
    tournaments (beyond ceil(log2(n)) rounds). A full maximum-weight matching
    (Blossom algorithm) would be required to guarantee no repeats in that case.
    """

    @pytest.mark.parametrize("num_players", range(7, 33))
    def test_no_repeat_pairs_higher_rated_always_wins(self, num_players: int):
        num_rounds = math.ceil(math.log2(num_players))
        repeats = _simulate_tournament(num_players, num_rounds)
        assert not repeats, (
            f"{num_players} players, {num_rounds} rounds — repeat pairings:\n"
            + "\n".join(repeats)
        )
