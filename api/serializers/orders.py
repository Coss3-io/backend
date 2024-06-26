from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from django.db.models import F, DecimalField, ExpressionWrapper, Sum
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
    compute_order_hash,
    encode_order,
)


class TimestampField(serializers.Field):
    """Class used to change from timestamp to datetime"""

    def to_internal_value(self, data):
        timestamp = int(validate_decimal_integer(data, "expiry"))
        return datetime.fromtimestamp(timestamp)

    def to_representation(self, value: datetime):
        return int(datetime.timestamp(value))


class BotSerializer(serializers.ModelSerializer):
    """The model used to serialize bots"""

    bot_hash = serializers.CharField(required=False, read_only=True)
    address = serializers.CharField(required=True, allow_blank=False, write_only=True)
    base_token = serializers.CharField(
        required=True, allow_blank=False, write_only=True
    )
    quote_token = serializers.CharField(
        required=True, allow_blank=False, write_only=True
    )
    quote_token = serializers.CharField(
        required=True, allow_blank=False, write_only=True
    )
    amount = serializers.DecimalField(
        write_only=True,
        required=True,
        max_digits=78,
        decimal_places=0,
    )
    expiry = TimestampField(required=True, write_only=True)
    signature = serializers.CharField(
        required=True,
        write_only=True,
    )
    is_buyer = serializers.BooleanField(allow_null=True, default=None, write_only=True)  # type: ignore
    timestamp = TimestampField(required=False, read_only=True)
    base_token_amount = serializers.DecimalField(
        read_only=True,
        max_digits=78,
        decimal_places=0,
    )
    quote_token_amount = serializers.DecimalField(
        read_only=True,
        max_digits=78,
        decimal_places=0,
    )

    class Meta:
        model = Bot
        fields = [
            "address",
            "bot_hash",
            "expiry",
            "base_token_amount",
            "quote_token_amount",
            "signature",
            "is_buyer",
            "step",
            "price",
            "amount",
            "chain_id",
            "base_token",
            "quote_token",
            "maker_fees",
            "upper_bound",
            "lower_bound",
            "fees_earned",
            "timestamp",
        ]
        extra_kwargs = {
            "fees_earned": {"read_only": True},
        }

    async def create(self, validated_data):
        """Used to create the orders for the created bot"""

        user = (await User.objects.aget_or_create(address=validated_data["address"]))[0]
        validated_data.update({"user": user})
        del validated_data["address"]
        amount = validated_data.pop("amount")
        base_token = validated_data.pop("base_token")
        quote_token = validated_data.pop("quote_token")
        signature = validated_data.pop("signature")
        expiry = validated_data.pop("expiry")
        is_buyer = validated_data.pop("is_buyer")

        bot = await Bot.objects.acreate(**validated_data)
        orders = [
            Maker(
                bot=bot,
                base_token=base_token,
                quote_token=quote_token,
                amount=amount,
                price=str(price),
                is_buyer=price <= int(validated_data["price"]),
                expiry=expiry,
                chain_id=int(validated_data["chain_id"]),
                signature=signature,
            )
            for price in range(
                int(validated_data["lower_bound"]),
                (int(validated_data["upper_bound"])) + 1,
                int(validated_data["step"]),
            )
        ]

        for order in orders:
            _, order.order_hash = compute_order_hash(
                {
                    "address": user.address,
                    "amount": int(order.amount),
                    "price": int(validated_data.get("price")),
                    "step": int(validated_data["step"]),
                    "maker_fees": int(validated_data["maker_fees"]),
                    "upper_bound": int(validated_data["upper_bound"]),
                    "lower_bound": int(validated_data["lower_bound"]),
                    "base_token": order.base_token,
                    "quote_token": order.quote_token,
                    "expiry": int(order.expiry.timestamp()),
                    "chain_id": int(order.chain_id),
                    "is_buyer": 0 if is_buyer else 1,
                    "replace_order": True,
                    "maker_price": int(order.price),
                }
            )
        await Maker.objects.abulk_create(orders)
        return bot

    def validate_is_buyer(self, value):
        if value is None:
            raise ValidationError("This field is required.")
        return value

    def validate_price(self, value):
        """Validates that the price sent is an integer"""
        return validate_decimal_integer(value, "price")

    def validate_amount(self, value):
        """Validates that the amount sent is an integer"""
        return validate_decimal_integer(value, "amount")

    def validate_base_token(self, value):
        """Validates the base_token format"""
        return validate_address(value, "base_token")

    def validate_quote_token(self, value):
        """Validates the quote_token format"""
        return validate_address(value, "quote_token")

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

    def validate_step(self, data: str):
        """Validated the step, step cannot be negative"""
        return validate_decimal_integer(data, name="step")

    def validate_signature(self, data: str):
        """Validated the signature send by the user"""
        return Signature(data)

    def validate(self, data: BotTypedDict):
        """Used to validate the bounds of the bot"""

        if Decimal(data["lower_bound"]) >= Decimal(data["upper_bound"]):
            raise ValidationError(errors.Order.LOWER_BOUND_GTE_UPPER_BOUND)
        if Decimal(data["lower_bound"]) > Decimal(data["price"]):
            raise ValidationError(errors.Order.LOWER_BOUND_GT_PRICE)
        if Decimal(data["price"]) > Decimal(data["upper_bound"]):
            raise ValidationError(errors.Order.PRICE_GT_UPPER_BOUND)
        if data["base_token"].lower() == data["quote_token"].lower():
            raise ValidationError(errors.Order.SAME_BASE_QUOTE_ERROR)

        encoded_order = encode_order(
            {
                "address": data["address"],
                "amount": int(data["amount"]),
                "price": int(data["price"]),
                "step": int(data["step"]),
                "maker_fees": int(data["maker_fees"]),
                "upper_bound": int(data["upper_bound"]),
                "lower_bound": int(data["lower_bound"]),
                "base_token": data["base_token"],
                "quote_token": data["quote_token"],
                "expiry": int(data["expiry"].timestamp()),
                "chain_id": int(data["chain_id"]),
                "is_buyer": 0 if data["is_buyer"] else 1,
                "replace_order": True,
            }
        )
        data["bot_hash"] = str(Web3.to_hex(Web3.keccak(encoded_order)))

        if (
            validate_eth_signed_message(
                message=encoded_order,
                signature=data["signature"],
                address=data["address"],
            )
            == False
        ):
            raise ValidationError(errors.Signature.SIGNATURE_MISMATCH_ERROR)

        return super().validate(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["address"] = instance.user.address
        if not self.context.get("bot", None):
            return data

        data.update(
            {
                "base_token": instance.orders.all()[0].base_token,
                "quote_token": instance.orders.all()[0].quote_token,
                "expiry": int(instance.orders.all()[0].expiry.timestamp()),
                "amount": "{0:f}".format(instance.orders.all()[0].amount),
            }
        )
        return data


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
    address = serializers.CharField()
    expiry = TimestampField(required=True)
    bot = BotSerializer(read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)
    is_buyer = serializers.BooleanField(allow_null=True, default=None)  # type: ignore
    timestamp = TimestampField(required=False, read_only=True)
    base_fees = serializers.DecimalField(
        read_only=True,
        max_digits=78,
        decimal_places=0,
    )
    quote_fees = serializers.DecimalField(
        read_only=True,
        max_digits=78,
        decimal_places=0,
    )

    class Meta:
        model = Maker
        fields = [
            "id",
            "bot",
            "base_fees",
            "quote_fees",
            "address",
            "base_token",
            "quote_token",
            "amount",
            "price",
            "is_buyer",
            "expiry",
            "chain_id",
            "order_hash",
            "status",
            "filled",
            "signature",
            "timestamp",
        ]
        extra_kwargs = {
            "user": {"write_only": True},
            "filled": {"read_only": True},
        }
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
        if self.context.get("public", None):
            del data["base_fees"]
            del data["quote_fees"]
            return data
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
        if data["base_token"].lower() == data["quote_token"].lower():
            raise ValidationError(errors.Order.SAME_BASE_QUOTE_ERROR)

        encoded_order, order_hash = compute_order_hash(
            {
                "address": data["address"],
                "amount": int(data["amount"]),
                "price": int(data["price"]),
                "step": 0,
                "maker_fees": 0,
                "upper_bound": 0,
                "lower_bound": 0,
                "base_token": data["base_token"],
                "quote_token": data["quote_token"],
                "expiry": int(data["expiry"].timestamp()),
                "chain_id": int(data["chain_id"]),
                "is_buyer": 0 if data["is_buyer"] else 1,
                "replace_order": False,
            }
        )

        if (
            validate_eth_signed_message(
                message=encoded_order,
                signature=data["signature"],
                address=data["address"],
            )
            == False
        ):
            raise ValidationError(errors.Signature.SIGNATURE_MISMATCH_ERROR)

        if order_hash != data["order_hash"]:
            raise ValidationError(errors.KeccakHash.MISMATCH_HASH_ERROR)
        return super().validate(data)


class TakerListSerializer(serializers.ListSerializer):
    """List serializer for batch creation of taker orders"""

    async def create(self, validated_data):
        takers = [Taker(**order) for order in validated_data]
        return await Taker.objects.abulk_create(takers)


class TakerSerializer(serializers.ModelSerializer):
    """Serializer used for the taker orders creation and deletetion"""

    maker = MakerSerializer(required=False, write_only=True)
    maker_id = serializers.IntegerField(required=True, write_only=True)
    timestamp = TimestampField(required=False, read_only=True)

    class Meta:
        model = Taker
        list_serializer_class = TakerListSerializer
        fields = [
            "maker",
            "maker_id",
            "block",
            "amount",
            "base_fees",
            "fees",
            "is_buyer",
            "timestamp",
        ]
        extra_kwargs = {
            "user": {"write_only": True},
        }

    def validate_block(self, data: str) -> str:
        return validate_decimal_integer(data, "block")

    def validate_amount(self, data: str) -> str:
        return validate_decimal_integer(data, "amount")

    def validate_fees(self, data: str) -> str:
        return validate_decimal_integer(data, "fees")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.maker.bot is not None:
            if not instance.is_buyer:
                data["price"] = "{0:f}".format(
                    Decimal(
                        (instance.maker.price)
                        / Decimal((1000 + instance.maker.bot.maker_fees) / 1000)
                    ).quantize(Decimal("1."))
                )
            else:
                data["price"] = "{0:f}".format(
                    Decimal(
                        (instance.maker.price)
                        * Decimal((1000 + instance.maker.bot.maker_fees) / 1000)
                    ).quantize(Decimal("1."))
                )
        else:
            data["price"] = "{0:f}".format(instance.maker.price)
        return data
