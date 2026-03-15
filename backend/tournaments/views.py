
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from participants.models import Participant

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
