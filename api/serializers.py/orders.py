from eth_abi.packed import encode_packed
from rest_framework import serializers
from rest_framework.validators import ValidationError
from models.orders import Maker, Taker
from models.types import MakerTypedDict
from api.utils import validate_eth_signed_message
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

    id = serializers.IntegerField()

    class Meta:
        model = Maker
        list_serializer_class = MakerListSerializer

    def validate(self, data: MakerTypedDict):
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
                data["owner"],
                data["amount"],
                data["price"],
                0,  # this is the step field
                0,  # this is the maker fees field
                0,  # this is the upper bound field
                0,  # this is the lower bound field
                data["base_token"],
                data["quote_token"],
                data["expiry"],
                0 if data["is_buyer"] else 1,
                False,  # not a replace order
            ],
        )

        orderHash = str(Web3.solidity_keccak([message], ["bytes"]))

        if (
            validate_eth_signed_message(
                message=f'"\x19Ethereum Signed Message:\n32"{message}',
                signature=data["signature"],
                address=data["owner"].address,
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

    def create(self, validated_data):
        takers = [Taker(**order) for order in validated_data]
        return Taker.objects.bulk_create(takers)


class TakerSerializer(serializers.ModelSerializer):
    """Serializer used for the taker orders creation and deletetion"""

    class Meta:
        model = Maker
        list_serializer_class = TakerListSerializer
