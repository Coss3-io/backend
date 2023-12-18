from rest_framework.serializers import ModelSerializer, CharField, BooleanField
from rest_framework.validators import ValidationError
from api.errors import General
from api.models.stacking import Stacking, StackingFees, StackingFeesWithdrawal
from api.utils import validate_address, validate_decimal_integer


class StackingSerializer(ModelSerializer):
    """Class used to serialize user stacking entries"""

    address = CharField(required=True, allow_blank=False, write_only=True)
    withdraw = BooleanField(allow_null=True, default=None, write_only=True)  # type: ignore

    async def create(self, validated_data):
        del validated_data["amount"]
        del validated_data["address"]
        del validated_data["withdraw"]
        return (await Stacking.objects.aget_or_create(**validated_data))[0]

    class Meta:
        model = Stacking
        fields = ["slot", "amount", "address", "withdraw", "chain_id"]

    def validate_withdraw(self, value):
        if value is None:
            raise ValidationError(General.MISSING_FIELD)
        return value

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
        fields = ["token", "amount", "slot", "chaid_id"]

    def validate_token(self, value):
        return validate_address(value, "token")


class StackingFeesWithdrawalSerializer(ModelSerializer):
    """Class for serializing stacking withdrawal entries"""

    address = CharField(required=True, allow_blank=False, write_only=True)

    async def create(self, validated_data):
        del validated_data["address"]
        return (await StackingFeesWithdrawal.objects.aget_or_create(**validated_data))[
            0
        ]

    class Meta:
        model = StackingFeesWithdrawal
        fields = ["token", "slot", "address", "chain_id"]

    def validate_token(self, value):
        return validate_address(value, "token")

    def validate_address(self, value):
        return validate_address(value, "")
