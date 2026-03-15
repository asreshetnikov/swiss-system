from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from standings.calculator import calculate_standings
from standings.models import StandingSnapshot
from tournaments.models import Tournament


def _get_tournament(slug):
    try:
        return Tournament.objects.get(slug=slug)
    except Tournament.DoesNotExist:
        raise NotFound("Tournament not found")


class CurrentStandingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        tournament = _get_tournament(slug)
        data = calculate_standings(tournament)
        return Response({"standings": data})


class RoundStandingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug, round_number):
        tournament = _get_tournament(slug)
        try:
            round_obj = tournament.rounds.get(number=round_number)
        except Exception:
            raise NotFound(f"Round {round_number} not found")

        try:
            snapshot = StandingSnapshot.objects.get(
                tournament=tournament, round=round_obj
            )
        except StandingSnapshot.DoesNotExist:
            raise NotFound(f"No snapshot found for round {round_number}")

        return Response({"standings": snapshot.data, "round": round_number})
