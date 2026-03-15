from django.urls import path

from .views import (
    ParticipantDetailView,
    ParticipantListCreateView,
    ParticipantWithdrawView,
)

urlpatterns = [
    path("", ParticipantListCreateView.as_view(), name="participant-list"),
    path("<int:pk>/", ParticipantDetailView.as_view(), name="participant-detail"),
    path("<int:pk>/withdraw/", ParticipantWithdrawView.as_view(), name="participant-withdraw"),
]
