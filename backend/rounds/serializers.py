from rest_framework import serializers

from .models import Pairing, Round


class PairingSerializer(serializers.ModelSerializer):
    white_name = serializers.CharField(source="white.name", read_only=True, allow_null=True)
    black_name = serializers.CharField(source="black.name", read_only=True, allow_null=True)
    white_seed = serializers.IntegerField(source="white.seed", read_only=True, allow_null=True)
    black_seed = serializers.IntegerField(source="black.seed", read_only=True, allow_null=True)

    class Meta:
        model = Pairing
        fields = (
            "id", "board_number",
            "white", "white_name", "white_seed",
            "black", "black_name", "black_seed",
            "result", "is_bye", "note",
        )
        read_only_fields = ("id", "board_number", "white", "black", "is_bye")


class PairingResultSerializer(serializers.Serializer):
    result = serializers.ChoiceField(choices=Pairing.Result.choices)
    note = serializers.CharField(required=False, allow_blank=True)


class RoundSerializer(serializers.ModelSerializer):
    pairings = PairingSerializer(many=True, read_only=True)

    class Meta:
        model = Round
        fields = ("id", "number", "status", "created_at", "pairings")
        read_only_fields = ("id", "number", "status", "created_at")


class RoundListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Round
        fields = ("id", "number", "status", "created_at")
        read_only_fields = ("id", "number", "status", "created_at")
