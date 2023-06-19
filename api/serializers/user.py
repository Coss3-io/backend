import api.errors as errors
from time import time
from rest_framework import serializers
from rest_framework.validators import ValidationError
from api.models import User
from api.models.types import UserTypedDict, Address, Signature
from api.utils import validate_eth_signed_message, validate_decimal_integer

class GenericField(serializers.Field):

    def to_internal_value(self, data):
        return data
    def to_representation(self, value):
        return value

class UserSerializer(serializers.ModelSerializer):
    """The user class serializer"""

    timestamp = GenericField(write_only=True)
    signature = GenericField(write_only=True)

    class Meta:
        model = User
        fields = ["address", "timestamp", "signature"]

    def create(self, validated_data: UserTypedDict):
        return User.objects.create_user(validated_data["address"])

    def validate_timestamp(self, value):
        user_timestamp = int(validate_decimal_integer(value, "timestamp"))
        timestamp = int(time())

        if (timestamp - user_timestamp) > 120:
            raise ValidationError(errors.User.USER_TIMESTAMP_ERROR)
        return user_timestamp

    def validate_address(self, value: str):
        return Address(value)

    def validate(self, data):

        signature = Signature(data["signature"])
        if (
            validate_eth_signed_message(
                message=f"coss3.io account creation with timestamp {data['timestamp']}".encode(),
                signature=signature,
                address=data["address"],
            )
            == False
        ):
            raise ValidationError(errors.Signature.SIGNATURE_MISMATCH_ERROR)
        return super().validate(data)
