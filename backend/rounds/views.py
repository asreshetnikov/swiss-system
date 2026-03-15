from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditLog
from pairing.engine import PlayerState, generate_pairings
from standings.calculator import save_snapshot
from tournaments.models import Tournament

from .models import Pairing, Round
from .serializers import (
    PairingResultSerializer,
    PairingSerializer,
    RoundListSerializer,
    RoundSerializer,
)


def _get_tournament(slug):
    try:
        return Tournament.objects.get(slug=slug)
    except Tournament.DoesNotExist:
        raise NotFound("Tournament not found")


def _get_round(tournament, number):
    try:
        return tournament.rounds.get(number=number)
    except Round.DoesNotExist:
        raise NotFound(f"Round {number} not found")


def _require_owner(request, tournament):
    if tournament.owner != request.user:
        raise PermissionDenied("Only the owner can perform this action")


def _build_player_states(tournament: Tournament, round_number: int) -> list[PlayerState]:
    """Build PlayerState list from DB for pairing engine."""
    participants = list(tournament.participants.all())
    closed_rounds = list(
        tournament.rounds.filter(
            status=Round.Status.CLOSED, number__lt=round_number
        ).order_by("number")
    )

    bye_points = tournament.bye_points
    states: dict[int, PlayerState] = {}

    for p in participants:
        states[p.id] = PlayerState(
            id=p.id,
            seed=p.seed or 9999,
            points=Decimal("0"),
            colors_history=[],
            opponents_history=[],
            bye_received=False,
            status=p.status,
        )

    for round_obj in closed_rounds:
        for pairing in round_obj.pairings.all():
            if pairing.is_bye and pairing.white_id:
                pid = pairing.white_id
                if pid in states:
                    states[pid].points += Decimal(str(bye_points))
                    states[pid].bye_received = True
                continue

            w_id = pairing.white_id
            b_id = pairing.black_id
            result = pairing.result

            if w_id and w_id in states:
                states[w_id].colors_history.append("W")
                if b_id:
                    states[w_id].opponents_history.append(b_id)

            if b_id and b_id in states:
                states[b_id].colors_history.append("B")
                if w_id:
                    states[b_id].opponents_history.append(w_id)

            if result == Pairing.Result.WHITE_WIN:
                if w_id and w_id in states:
                    states[w_id].points += Decimal("1")
            elif result == Pairing.Result.BLACK_WIN:
                if b_id and b_id in states:
                    states[b_id].points += Decimal("1")
            elif result == Pairing.Result.DRAW:
                if w_id and w_id in states:
                    states[w_id].points += Decimal("0.5")
                if b_id and b_id in states:
                    states[b_id].points += Decimal("0.5")

    return list(states.values())


class RoundListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        tournament = _get_tournament(slug)
        rounds = tournament.rounds.all()
        return Response(RoundListSerializer(rounds, many=True).data)


class GenerateRoundView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, slug):
        tournament = _get_tournament(slug)
        _require_owner(request, tournament)

        if tournament.status != Tournament.Status.RUNNING:
            raise ValidationError("Tournament must be in RUNNING status to generate rounds")

        # Check existing rounds
        existing_rounds = list(tournament.rounds.order_by("number"))

        # Block if latest round is not closed
        if existing_rounds:
            latest = existing_rounds[-1]
            if latest.status != Round.Status.CLOSED:
                raise ValidationError(
                    f"Round {latest.number} must be closed before generating a new round"
                )

        next_number = len(existing_rounds) + 1
        if next_number > tournament.num_rounds:
            raise ValidationError(
                f"All {tournament.num_rounds} rounds have already been generated"
            )

        # Build player states and generate pairings
        player_states = _build_player_states(tournament, next_number)
        pairs = generate_pairings(next_number, player_states)

        # Create Round and Pairings
        round_obj = Round.objects.create(tournament=tournament, number=next_number)

        board = 1
        # Byes first have no board number issue, but let's put games first
        game_pairs = [p for p in pairs if not p.is_bye]
        bye_pairs = [p for p in pairs if p.is_bye]

        for pair in game_pairs:
            Pairing.objects.create(
                round=round_obj,
                board_number=board,
                white_id=pair.white_id,
                black_id=pair.black_id,
                is_bye=False,
            )
            board += 1

        for pair in bye_pairs:
            Pairing.objects.create(
                round=round_obj,
                board_number=board,
                white_id=pair.white_id,
                black_id=None,
                is_bye=True,
                result=Pairing.Result.BYE,
            )
            board += 1

        AuditLog.objects.create(
            tournament=tournament,
            actor=request.user,
            action="generate_round",
            entity_type="Round",
            entity_id=round_obj.id,
            after={"round_number": next_number},
        )

        return Response(RoundSerializer(round_obj).data, status=status.HTTP_201_CREATED)


class PublishRoundView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, slug, number):
        tournament = _get_tournament(slug)
        _require_owner(request, tournament)
        round_obj = _get_round(tournament, number)

        if round_obj.status != Round.Status.DRAFT:
            raise ValidationError("Round is not in DRAFT status")

        round_obj.status = Round.Status.PUBLISHED
        round_obj.save()

        AuditLog.objects.create(
            tournament=tournament,
            actor=request.user,
            action="publish_round",
            entity_type="Round",
            entity_id=round_obj.id,
            after={"status": "PUBLISHED"},
        )
        return Response(RoundListSerializer(round_obj).data)


class RoundPairingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug, number):
        tournament = _get_tournament(slug)
        round_obj = _get_round(tournament, number)
        return Response(RoundSerializer(round_obj).data)


class PairingResultView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, slug, number, pairing_id):
        tournament = _get_tournament(slug)
        _require_owner(request, tournament)
        round_obj = _get_round(tournament, number)

        if round_obj.status == Round.Status.DRAFT:
            raise ValidationError("Publish the round before entering results")
        if round_obj.status == Round.Status.CLOSED:
            raise ValidationError("Round is already closed")

        try:
            pairing = round_obj.pairings.get(id=pairing_id)
        except Pairing.DoesNotExist:
            raise NotFound("Pairing not found")

        if pairing.is_bye:
            raise ValidationError("Cannot change result of a bye pairing")

        serializer = PairingResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        before = {"result": pairing.result, "note": pairing.note}
        pairing.result = serializer.validated_data["result"]
        if "note" in serializer.validated_data:
            pairing.note = serializer.validated_data["note"]
        pairing.save()

        AuditLog.objects.create(
            tournament=tournament,
            actor=request.user,
            action="set_result",
            entity_type="Pairing",
            entity_id=pairing.id,
            before=before,
            after={"result": pairing.result, "note": pairing.note},
            reason=serializer.validated_data.get("note", ""),
        )

        return Response(PairingSerializer(pairing).data)


class CloseRoundView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, slug, number):
        tournament = _get_tournament(slug)
        _require_owner(request, tournament)
        round_obj = _get_round(tournament, number)

        if round_obj.status != Round.Status.PUBLISHED:
            raise ValidationError("Round must be PUBLISHED before closing")

        # Check all non-bye pairings have results
        pending = round_obj.pairings.filter(
            result=Pairing.Result.PENDING, is_bye=False
        ).count()
        if pending > 0:
            raise ValidationError(
                f"Cannot close round: {pending} pairing(s) still have PENDING results"
            )

        round_obj.status = Round.Status.CLOSED
        round_obj.save()

        # Save standings snapshot
        save_snapshot(tournament, round_obj)

        # If last round, finish tournament
        if round_obj.number >= tournament.num_rounds:
            tournament.status = Tournament.Status.FINISHED
            tournament.save()

        AuditLog.objects.create(
            tournament=tournament,
            actor=request.user,
            action="close_round",
            entity_type="Round",
            entity_id=round_obj.id,
            after={"status": "CLOSED"},
        )

        return Response(RoundListSerializer(round_obj).data)
