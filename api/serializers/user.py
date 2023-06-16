import api.errors as errors
from time import time
from rest_framework import serializers
from rest_framework.validators import ValidationError
from api.models import User
from api.models.types import UserTypedDict
from api.utils import validate_eth_signed_message, validate_decimal_integer


class UserSerializer(serializers.ModelSerializer):
    """The user class serializer"""

    class Meta:
        model = User
        fields = ["address"]

    def create(self, validated_data: UserTypedDict):
        return User.objects.create_user(validated_data["address"])

    def validate(self, data: UserTypedDict):
        user_timestamp = int(
            validate_decimal_integer(self.context["timestamp"], "timestamp")
        )
        signature = self.context["signature"]
        timestamp = int(time())

        if (timestamp - user_timestamp) > 120:
            raise ValidationError(errors.User.USER_TIMESTAMP_ERROR)

        if (
            validate_eth_signed_message(
                message=f"coss3.io account creation with timstamp {user_timestamp}".encode(),
                signature=signature,
                address=data["address"],
            )
            == False
        ):
            raise ValidationError(errors.Signature.SIGNATURE_MISMATCH_ERROR)
        return super().validate(data)
