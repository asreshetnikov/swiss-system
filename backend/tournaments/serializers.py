from rest_framework import serializers

from .models import Tournament


class TournamentSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)

    class Meta:
        model = Tournament
        fields = (
            "id", "slug", "name", "description", "time_control",
            "num_rounds", "bye_points", "status", "is_public",
            "owner_email", "created_at", "updated_at",
        )
        read_only_fields = ("id", "slug", "owner_email", "status", "created_at", "updated_at")


class TournamentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Tournament.Status.choices)

    VALID_TRANSITIONS = {
        Tournament.Status.DRAFT: [Tournament.Status.OPEN],
        Tournament.Status.OPEN: [Tournament.Status.RUNNING, Tournament.Status.DRAFT],
        Tournament.Status.RUNNING: [Tournament.Status.FINISHED],
        Tournament.Status.FINISHED: [Tournament.Status.ARCHIVED],
        Tournament.Status.ARCHIVED: [],
    }

    def validate(self, data):
        tournament = self.context["tournament"]
        current = tournament.status
        new = data["status"]
        allowed = self.VALID_TRANSITIONS.get(current, [])
        if new not in allowed:
            raise serializers.ValidationError(
                f"Cannot transition from {current} to {new}. "
                f"Allowed: {allowed}"
            )
        return data
