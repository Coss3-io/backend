from time import time
from decimal import Decimal
from rest_framework import serializers
from rest_framework.validators import ValidationError
from api.models import User
from api.models.types import UserTypedDict, BotTypedDict
from api.models.orders import Bot
from api.utils import validate_eth_signed_message

class BotSerializer(serializers.ModelSerializer):
    """The model used to serialize bots"""

    class Meta:
        model: Bot

    def validate_maker_fees(self, data: Decimal):
        """Validated the maker fees field, maker fees cannot be negative"""
        if data <= Decimal("0"):
            raise ValidationError("maker_fees cannot be negative")
        return data
    
    def validate_step(self, data: Decimal):
        """Validated the step, step cannot be negative"""
        if data <= Decimal("0"):
            raise ValidationError("step cannot be negative")
        return data

    def validate(self, data: BotTypedDict):
        """Used to validate the bounds of the bot"""

        if data["lower_bound"] >= data["upper_bound"]:
            raise ValidationError("upper_bound must be higher than the lower_bound")
        if data["lower_bound"] > data["price"]:
            raise ValidationError("lower_bound cannot be bigger than price")
        if data["price"] > data["upper_bound"]:
            raise ValidationError("price cannot be bigger than upper_bound")
        return super().validate(data)


class UserSerializer(serializers.ModelSerializer):
    """The user class serializer"""

    class Meta:
        model = User

    def create(self, validated_data: UserTypedDict):
        User.objects.create_user(validated_data["address"])

    def validate(self, data: UserTypedDict):
        user_timestamp = self.context["timestamp"]
        signature = self.context["signature"]
        timestamp = int(time())

        if (timestamp - user_timestamp) > 120:
            raise ValidationError(
                "The submitted timestamp for account creation is too old"
            )

        if (
            validate_eth_signed_message(
                message=f"Coss.io account creation with timstamp {user_timestamp}",
                signature=signature,
                address=data["address"],
            )
            == False
        ):
            raise ValidationError("The signature provided does not match the address")
        return super().validate(data)
