from decimal import Decimal, ROUND_DOWN
from eth_abi.packed import encode_packed
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.validators import ValidationError
from api.models.orders import Maker, Taker, Bot
from api.models.types import MakerTypedDict, BotTypedDict, KeccakHash, Signature
from api.utils import (
    validate_eth_signed_message,
    validate_decimal_integer,
    validate_address,
)
from web3 import Web3


class MakerListSerializer(serializers.ListSerializer):
    """Used for multiple operation on orders, especially creation, and update"""

    def create(self, validated_data):
        makers = [Maker(**data) for data in validated_data]
        return Maker.objects.bulk_create(makers)

    def update(self, validated_data):
        return Maker.objects.bulk_update(
            [Maker(**data) for data in validated_data], ["filled", "status"]
        )


class MakerSerializer(serializers.ModelSerializer):
    """The maker order class serializer"""

    id = serializers.IntegerField(required=False)

    class Meta:
        model = Maker
        fields = [
            "id",
            "base_token",
            "quote_token",
            "amount",
            "price",
            "is_buyer",
            "expiry",
            "order_hash",
            "signature",
        ]
        list_serializer_class = MakerListSerializer

    def validate_amount(self, value: str):
        return validate_decimal_integer(value, "amount")

    def validate_price(self, value: str):
        return validate_decimal_integer(value, "price")

    def validate_expiry(self, value: str):
        return validate_decimal_integer(value, "expiry")

    def validate_base_token(self, value):
        return validate_address(value, "base_token")

    def validate_quote_token(self, value):
        return validate_address(value, "quote_token")

    def validate_order_hash(self, value):
        return KeccakHash(value)

    def validate_signature(self, value):
        return Signature(value)

    def validate(self, data):
        print(data)
        message = encode_packed(
            [
                "address",
                "uint256",
                "uint256",
                "uint256",
                "uint256",
                "uint256",
                "uint256",
                "address",
                "address",
                "uint64",
                "uint8",
                "bool",
            ],
            [
                self.context["user"].address,
                self.data["amount"],
                self.data["price"],
                0,  # this is the step field
                0,  # this is the maker fees field
                0,  # this is the upper bound field
                0,  # this is the lower bound field
                self.data["base_token"],
                self.data["quote_token"],
                self.data["expiry"],
                0 if self.data["is_buyer"] else 1,
                False,  # not a replace order
            ],
        )

        orderHash = str(Web3.solidity_keccak([message], ["bytes"]))

        if (
            validate_eth_signed_message(
                message=f'"\x19Ethereum Signed Message:\n32"{message}',
                signature=self.data["signature"],
                address=self.context["user"].address,
            )
            == False
        ):
            raise ValidationError("The signature sent doesn't match the order owner")

        if orderHash != self.data["order_hash"]:
            raise ValidationError(
                "The provided order hash does not match the computed hash"
            )
        return super().validate(self.data)


class TakerListSerializer(serializers.ListSerializer):
    """List serializer for batch creation of taker orders"""

    def create(self, validated_data):
        takers = [Taker(**order) for order in validated_data]
        return Taker.objects.bulk_create(takers)


class TakerSerializer(serializers.ModelSerializer):
    """Serializer used for the taker orders creation and deletetion"""

    class Meta:
        model = Maker
        list_serializer_class = TakerListSerializer


class BotSerializer(serializers.ModelSerializer):
    """The model used to serialize bots"""

    orders = MakerSerializer()

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
