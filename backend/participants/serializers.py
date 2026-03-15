from rest_framework import serializers

from .models import Participant


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = ("id", "name", "rating", "seed", "status", "created_at")
        read_only_fields = ("id", "seed", "created_at")


class ParticipantWithdrawSerializer(serializers.Serializer):
    pass  # No extra data needed
