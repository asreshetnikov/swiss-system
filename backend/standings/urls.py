from django.urls import path

from .views import CurrentStandingsView, RoundStandingsView

urlpatterns = [
    path("", CurrentStandingsView.as_view(), name="standings-current"),
    path("<int:round_number>/", RoundStandingsView.as_view(), name="standings-round"),
]
