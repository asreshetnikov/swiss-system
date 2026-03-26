
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from participants.models import Participant
from rounds.models import Round
from standings.calculator import calculate_standings

from .models import Tournament
from .serializers import TournamentSerializer, TournamentStatusSerializer


class TournamentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Tournament.objects.filter(owner=request.user)
        return Response(TournamentSerializer(qs, many=True).data)

    def post(self, request):
        serializer = TournamentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tournament = serializer.save(owner=request.user)
        return Response(TournamentSerializer(tournament).data, status=status.HTTP_201_CREATED)


class TournamentDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def _get_tournament(self, slug):
        try:
            return Tournament.objects.get(slug=slug)
        except Tournament.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Tournament not found")

    def get(self, request, slug):
        tournament = self._get_tournament(slug)
        return Response(TournamentSerializer(tournament).data)

    def patch(self, request, slug):
        tournament = self._get_tournament(slug)
        if tournament.owner != request.user:
            raise PermissionDenied("Only the owner can edit this tournament")
        serializer = TournamentSerializer(tournament, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TournamentSerializer(tournament).data)


class TournamentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_tournament(self, slug):
        try:
            return Tournament.objects.get(slug=slug)
        except Tournament.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Tournament not found")

    @transaction.atomic
    def post(self, request, slug):
        tournament = self._get_tournament(slug)
        if tournament.owner != request.user:
            raise PermissionDenied("Only the owner can change tournament status")

        serializer = TournamentStatusSerializer(
            data=request.data, context={"tournament": tournament}
        )
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        # On transition to RUNNING: assign seeds
        if new_status == Tournament.Status.RUNNING:
            _assign_seeds(tournament)

        tournament.status = new_status
        tournament.save()
        return Response(TournamentSerializer(tournament).data)


class TournamentExportView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        tournament = get_object_or_404(Tournament, slug=slug)

        standings = calculate_standings(tournament)

        rounds = list(
            tournament.rounds
            .filter(status__in=[Round.Status.PUBLISHED, Round.Status.CLOSED])
            .prefetch_related("pairings__white", "pairings__black")
            .order_by("number")
        )
        round_numbers = [r.number for r in rounds]

        # Build crosstable: participant_id → round_number → {symbol, color, opponent}
        W_SYM = {"WHITE_WIN": "1", "BLACK_WIN": "0", "DRAW": "½", "FORFEIT": "FF", "PENDING": "—"}
        B_SYM = {"WHITE_WIN": "0", "BLACK_WIN": "1", "DRAW": "½", "FORFEIT": "FF", "PENDING": "—"}

        crosstable: dict = {row["participant_id"]: {} for row in standings}

        for round_obj in rounds:
            for pairing in round_obj.pairings.all():
                if pairing.is_bye and pairing.white_id:
                    if pairing.white_id in crosstable:
                        crosstable[pairing.white_id][round_obj.number] = {
                            "symbol": "bye", "color": None, "opponent": None
                        }
                elif pairing.white_id and pairing.black_id:
                    w_name = pairing.white.name if pairing.white else "—"
                    b_name = pairing.black.name if pairing.black else "—"
                    sym = pairing.result
                    if pairing.white_id in crosstable:
                        crosstable[pairing.white_id][round_obj.number] = {
                            "symbol": W_SYM.get(sym, "—"), "color": "W", "opponent": b_name
                        }
                    if pairing.black_id in crosstable:
                        crosstable[pairing.black_id][round_obj.number] = {
                            "symbol": B_SYM.get(sym, "—"), "color": "B", "opponent": w_name
                        }

        for row in standings:
            pid = row["participant_id"]
            row["round_results"] = [
                crosstable.get(pid, {}).get(rnum) for rnum in round_numbers
            ]

        return render(request, "tournaments/export.html", {
            "tournament": tournament,
            "standings": standings,
            "rounds": rounds,
            "round_numbers": round_numbers,
        })


def _assign_seeds(tournament: Tournament):
    """Assign seeds to participants when tournament starts. Rating desc, then insertion order."""
    participants = list(
        tournament.participants.filter(status=Participant.Status.ACTIVE).order_by(
            "-rating", "created_at"
        )
    )
    for i, p in enumerate(participants, start=1):
        p.seed = i
    Participant.objects.bulk_update(participants, ["seed"])
