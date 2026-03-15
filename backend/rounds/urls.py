from django.urls import path

from .views import (
    CloseRoundView,
    GenerateRoundView,
    PairingResultView,
    PublishRoundView,
    RoundListView,
    RoundPairingsView,
)

urlpatterns = [
    path("", RoundListView.as_view(), name="round-list"),
    path("generate/", GenerateRoundView.as_view(), name="round-generate"),
    path("<int:number>/publish/", PublishRoundView.as_view(), name="round-publish"),
    path("<int:number>/pairings/", RoundPairingsView.as_view(), name="round-pairings"),
    path(
        "<int:number>/pairings/<int:pairing_id>/",
        PairingResultView.as_view(),
        name="pairing-result",
    ),
    path("<int:number>/close/", CloseRoundView.as_view(), name="round-close"),
]
