from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from web3 import Web3
from eth_abi.packed import encode_packed
from rest_framework import serializers
from rest_framework.validators import ValidationError
from api.models import User
from api.models.orders import Maker, Taker, Bot
from api.models.types import BotTypedDict, KeccakHash, Signature, Address
import api.errors as errors
from api.utils import (
    validate_eth_signed_message,
    validate_decimal_integer,
    validate_address,
)


class TimestampField(serializers.Field):
    """Class used to change from timestamp to datetime"""

    def to_internal_value(self, data):
        timestamp = int(validate_decimal_integer(data, "expiry"))
        return datetime.fromtimestamp(timestamp)

    def to_representation(self, value: datetime):
        return int(datetime.timestamp(value))


class MakerListSerializer(serializers.ListSerializer):
    """Used for multiple operation on orders, especially creation, and update"""

    def create(self, validated_data):
        makers = [Maker(**data) for data in validated_data]
        return Maker.objects.abulk_create(makers)

    def update(self, validated_data):
        return Maker.objects.abulk_update(  # type: ignore
            [Maker(**data) for data in validated_data], ["filled", "status"]
        )


class MakerSerializer(serializers.ModelSerializer):
    """The maker order class serializer"""

    id = serializers.IntegerField(required=False, write_only=True)
    address = serializers.CharField(write_only=True)
    expiry = TimestampField(required=True)
    is_buyer = serializers.BooleanField(allow_null=True, default=None)  # type: ignore

    class Meta:
        model = Maker
        fields = [
            "id",
            "address",
            "base_token",
            "quote_token",
            "amount",
            "price",
            "is_buyer",
            "expiry",
            "order_hash",
            "signature",
        ]
        extra_kwargs = {"user": {"write_only": True}}
        list_serializer_class = MakerListSerializer

    async def create(self, validated_data):
        validated_data.update(
            {
                "user": (
                    await User.objects.aget_or_create(address=validated_data["address"])
                )[0]
            }
        )
        del validated_data["address"]
        return await super().create(validated_data=validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["address"] = instance.user.address
        return data

    def validate_id(self, value):
        if value is not None:
            raise ValidationError(errors.Order.ID_SUBMITTED_ERROR)

    def validate_address(self, value):
        return Address(value)

    def validate_is_buyer(self, value):
        if value is None:
            raise ValidationError("This field is required.")
        return value

    def validate_amount(self, value: str):
        return validate_decimal_integer(value, "amount")

    def validate_price(self, value: str):
        return validate_decimal_integer(value, "price")

    def validate_base_token(self, value):
        return validate_address(value, "base_token")

    def validate_quote_token(self, value):
        return validate_address(value, "quote_token")

    def validate_order_hash(self, value):
        return KeccakHash(value)

    def validate_signature(self, value):
        return Signature(value)

    def validate(self, data):
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
                data["address"],
                int(data["amount"]),
                int(data["price"]),
                0,  # this is the step field
                0,  # this is the maker fees field
                0,  # this is the upper bound field
                0,  # this is the lower bound field
                data["base_token"],
                data["quote_token"],
                int(data["expiry"].timestamp()),
                0 if data["is_buyer"] else 1,
                False,  # not a replace order
            ],
        )

        orderHash = str(Web3.to_hex(Web3.keccak(message)))

        if (
            validate_eth_signed_message(
                message=message,
                signature=data["signature"],
                address=data["address"],
            )
            == False
        ):
            raise ValidationError("The signature sent doesn't match the order owner")

        if orderHash != data["order_hash"]:
            raise ValidationError(
                "The provided order hash does not match the computed hash"
            )
        return super().validate(data)


class TakerListSerializer(serializers.ListSerializer):
    """List serializer for batch creation of taker orders"""

    async def create(self, validated_data):
        takers = [Taker(**order) for order in validated_data]
        return await Taker.objects.abulk_create(takers)


class TakerSerializer(serializers.ModelSerializer):
    """Serializer used for the taker orders creation and deletetion"""

    maker = MakerSerializer()

    class Meta:
        model = Taker
        list_serializer_class = TakerListSerializer
        depth = 1
        fields = [
            "maker",
            "block",
            "taker_amount",
            "base_fees",
            "fees",
            "is_buyer",
        ]
        extra_kwargs = {
            "user": {"write_only": True},
        }

        def validate_block(self, data: str) -> str:
            return validate_decimal_integer(data, "block")

        def validate_taker_amount(self, data: str) -> str:
            return validate_decimal_integer(data, "taker_amount")

        def validate_base_fees(self, data: str) -> str:
            return validate_decimal_integer(data, "base_fees")


class BotSerializer(serializers.ModelSerializer):
    """The model used to serialize bots"""

    address = serializers.CharField(required=True, allow_blank=False, write_only=True)
    expiry = TimestampField(required=True, write_only=True)

    class Meta:
        model: Bot

    async def create(self, validated_data):
        """Used to create the orders for the created bot"""
        user = (await User.objects.aget_or_create(address=validated_data["address"]))[0]
        validated_data.update({"user": user})
        del validated_data["address"]

        bot = await Bot.objects.acreate(**validated_data)
        orders = [
            {
                "bot": bot,
                "base_token": validated_data["base_token"],
                "quote_token": validated_data["quote_token"],
                "amount": validated_data["amount"],
                "price": str(price),
                "is_buyer": True if price <= int(validated_data["price"]) else False,
                "expiry": validated_data["expiry"],
                "signature": validated_data["signature"],
            }
            for price in range(
                int(validated_data["lower_bound"]),
                (int(validated_data["upper_bound"]) + int(validated_data["step"])),
                int(validated_data["step"]),
            )
        ]

        orders = [
            order
            | {
                "order_hash": str(
                    Web3.to_hex(
                        Web3.keccak(
                            encode_packed(
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
                                    user.address,
                                    order["amount"],
                                    order["price"],
                                    order["step"],
                                    order["maker_fees"],
                                    order["upper_bound"],
                                    order["lower_bound"],
                                    order["base_token"],
                                    order["quote_token"],
                                    int(order["expiry"].timestamp()),
                                    0 if order["is_buyer"] else 1,
                                    True,  # a replace order
                                ],
                            )
                        )
                    )
                )
            }
            for order in orders
        ]
        await Maker.objects.abulk_create(orders)
        return bot

    def validate_address(self, value):
        """Validates the address format"""
        return validate_address(value, "")

    def validate_upper_bound(self, value: str):
        """Validates the upper bound field as integer"""
        return validate_decimal_integer(value, name="upper_bound")

    def validate_lower_bound(self, value):
        """Validates the lower bound as integer"""
        return validate_decimal_integer(value, name="lower_bound")

    def validate_maker_fees(self, value: str):
        """Validated the maker fees field, maker fees cannot be negative"""
        return validate_decimal_integer(value, name="maker_fees")

    def validate_step(self, data: Decimal):
        """Validated the step, step cannot be negative"""
        if data <= Decimal("0"):
            raise ValidationError("step cannot be negative")
        return data

    def validate(self, data: BotTypedDict):
        """Used to validate the bounds of the bot"""

        if Decimal(data["lower_bound"]) >= Decimal(data["upper_bound"]):
            raise ValidationError("upper_bound must be higher than the lower_bound")
        if Decimal(data["lower_bound"]) > Decimal(data["price"]):
            raise ValidationError("lower_bound cannot be bigger than price")
        if Decimal(data["price"]) > Decimal(data["upper_bound"]):
            raise ValidationError("price cannot be bigger than upper_bound")

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
                data["address"],
                int(data["amount"]),
                int(data["price"]),
                int(data["step"]),
                int(data["maker_fees"]),
                int(data["upper_bound"]),
                int(data["lower_bound"]),
                data["base_token"],
                data["quote_token"],
                int(data["expiry"].timestamp()),
                0 if data["is_buyer"] else 1,
                True,  # a replace order
            ],
        )

        if (
            validate_eth_signed_message(
                message=message,
                signature=data["signature"],
                address=data["address"],
            )
            == False
        ):
            raise ValidationError("The signature sent doesn't match the order owner")

        return super().validate(data)
