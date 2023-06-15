from rest_framework.serializers import ModelSerializer
from api.models.stacking import Stacking


class StackingSerializer(ModelSerializer):
    """Class used to serialize user stacking entries"""

    class Meta:
        model = Stacking
        fields = ["token", "slot"]
        extra_kwargs = {"user": {"write_only": True}}
