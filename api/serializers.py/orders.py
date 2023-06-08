from rest_framework import serializers
from models.order import Maker
from models.types import MakerTypedDict
from rest_framework.validators import ValidationError
from eth_account import Account
from eth_abi.packed import encode_packed


class MakerSerializer(serializers.ModelSerializer):
    """The maker order class serializer"""

    class Meta:
        model = Maker

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
        if (
            Account.recover_message(f'"\x19Ethereum Signed Message:\n32"{message}', signature=data["signature"])
            != data["owner"]
        ):
            raise ValidationError("The signature sent doesn't match the order owner")
        return super().validate(data)
