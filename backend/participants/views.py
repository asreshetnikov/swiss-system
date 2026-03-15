from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tournaments.models import Tournament

from .models import Participant
from .serializers import ParticipantSerializer


def _get_tournament(slug):
    try:
        return Tournament.objects.get(slug=slug)
    except Tournament.DoesNotExist:
        raise NotFound("Tournament not found")


def _get_participant(tournament, pk):
    try:
        return tournament.participants.get(pk=pk)
    except Participant.DoesNotExist:
        raise NotFound("Participant not found")


class ParticipantListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, slug):
        tournament = _get_tournament(slug)
        participants = tournament.participants.all()
        return Response(ParticipantSerializer(participants, many=True).data)

    def post(self, request, slug):
        tournament = _get_tournament(slug)
        if tournament.owner != request.user:
            raise PermissionDenied("Only the owner can add participants")
        if tournament.status not in (Tournament.Status.DRAFT, Tournament.Status.OPEN):
            raise ValidationError("Cannot add participants to a running/finished tournament")
        serializer = ParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        participant = serializer.save(tournament=tournament)
        return Response(ParticipantSerializer(participant).data, status=status.HTTP_201_CREATED)


class ParticipantDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, slug, pk):
        tournament = _get_tournament(slug)
        if tournament.owner != request.user:
            raise PermissionDenied("Only the owner can edit participants")
        participant = _get_participant(tournament, pk)
        serializer = ParticipantSerializer(participant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ParticipantSerializer(participant).data)

    def delete(self, request, slug, pk):
        tournament = _get_tournament(slug)
        if tournament.owner != request.user:
            raise PermissionDenied("Only the owner can remove participants")
        if tournament.status not in (Tournament.Status.DRAFT, Tournament.Status.OPEN):
            raise ValidationError("Cannot delete participants from a running/finished tournament")
        participant = _get_participant(tournament, pk)
        participant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParticipantWithdrawView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug, pk):
        tournament = _get_tournament(slug)
        if tournament.owner != request.user:
            raise PermissionDenied("Only the owner can withdraw participants")
        participant = _get_participant(tournament, pk)
        if participant.status == Participant.Status.WITHDRAWN:
            raise ValidationError("Participant is already withdrawn")
        participant.status = Participant.Status.WITHDRAWN
        participant.save()
        return Response(ParticipantSerializer(participant).data)
