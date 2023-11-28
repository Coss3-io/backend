from rest_framework.serializers import ModelSerializer, CharField
from api.models.stacking import Stacking, StackingFees, StackingFeesWithdrawal
from api.utils import validate_address, validate_decimal_integer


class StackingSerializer(ModelSerializer):
    """Class used to serialize user stacking entries"""

    address = CharField(required=True, allow_blank=False, write_only=True)

    async def create(self, validated_data):
        del validated_data["amount"]
        del validated_data["address"]
        return (await Stacking.objects.aget_or_create(**validated_data))[0]

    class Meta:
        model = Stacking
        fields = ["slot", "amount", "address"]

    def validate_slot(self, value):
        return validate_decimal_integer(value, "slot")

    def validate_amount(self, value):
        return validate_decimal_integer(value, "amount")

    def validate_address(self, value):
        return validate_address(value, "")


class StackingFeesSerializer(ModelSerializer):
    """Class for serializing stacking fees entries"""

    async def create(self, validated_data):
        del validated_data["amount"]
        return (await StackingFees.objects.aget_or_create(**validated_data))[0]

    class Meta:
        model = StackingFees
        fields = ["token", "amount", "slot"]

    def validate_token(self, value):
        return validate_address(value, "token")


class StackingFeesWithdrawalSerializer(ModelSerializer):
    """Class for serializing stacking withdrawal entries"""

    address = CharField(required=True, allow_blank=False, write_only=True)

    async def create(self, validated_data):
        del validated_data["address"]
        return (await StackingFeesWithdrawal.objects.aget_or_create(**validated_data))[0]

    class Meta:
        model = StackingFeesWithdrawal
        fields = ["token", "slot", "address"]

    def validate_token(self, value):
        return validate_address(value, "token")

    def validate_address(self, value):
        return validate_address(value, "")
