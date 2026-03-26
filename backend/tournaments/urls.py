from django.urls import include, path

from .views import (
    TournamentDetailView,
    TournamentExportView,
    TournamentListCreateView,
    TournamentStatusView,
)

urlpatterns = [
    path("", TournamentListCreateView.as_view(), name="tournament-list"),
    path("<slug:slug>/", TournamentDetailView.as_view(), name="tournament-detail"),
    path("<slug:slug>/status/", TournamentStatusView.as_view(), name="tournament-status"),
    path("<slug:slug>/export/", TournamentExportView.as_view(), name="tournament-export"),
    path(
        "<slug:slug>/participants/",
        include("participants.urls"),
    ),
    path(
        "<slug:slug>/rounds/",
        include("rounds.urls"),
    ),
    path(
        "<slug:slug>/standings/",
        include("standings.urls"),
    ),
]
