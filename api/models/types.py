from typing import TypedDict, Any
from decimal import Decimal
from datetime import datetime
from rest_framework.validators import ValidationError
from web3 import Web3
import api.errors as errors


class Address(str):
    def __new__(cls, value, name=""):
        if len(value) <= 41:
            raise ValidationError(errors.Address.SHORT_ADDRESS_ERROR.format(name))
        if len(value) > 42:
            raise ValidationError(errors.Address.LONG_ADDRESS_ERROR.format(name))
        try:
            int(value, 0)
        except ValueError:
            raise ValidationError(errors.Address.WRONG_ADDRESS_ERROR.format(name))
        return super().__new__(cls, Web3.to_checksum_address(value))


class Signature(str):
    def __new__(cls, value):
        if len(value) <= 131:
            raise ValidationError(errors.Signature.SHORT_SIGNATURE_ERROR)
        if len(value) > 132:
            raise ValidationError(errors.Signature.LONG_SIGNATURE_ERROR)
        try:
            int(value, 0)
        except ValueError:
            raise ValidationError(errors.Signature.WRONG_SIGNATURE_ERROR)
        return super().__new__(cls, value)


class KeccakHash(str):
    def __new__(cls, value):
        if len(value) <= 65:
            raise ValidationError(errors.KeccakHash.SHORT_HASH_ERROR)
        if len(value) > 66:
            raise ValidationError(errors.KeccakHash.LONG_HASH_ERROR)
        try:
            int(value, 0)
        except ValueError:
            raise ValidationError(errors.KeccakHash.WRONG_HASH_ERROR)
        return super().__new__(cls, value)


class MakerTypedDict(TypedDict):
    user: Any
    base_token: Address
    quote_token: Address
    amount: Decimal
    price: Decimal
    is_buyer: bool
    expiry: datetime
    order_hash: str
    signature: str


class UserTypedDict(TypedDict):
    address: Address
    is_admin: bool
    is_active: bool


class BotTypedDict(TypedDict):
    bot_hash: str
    step: Decimal
    price: Decimal
    maker_fees: Decimal
    upper_bound: Decimal
    lower_bound: Decimal
    fees_earned: Decimal
    address: Address
    base_token: Address
    quote_token: Address
    amount: Decimal
    price: Decimal
    is_buyer: bool
    expiry: datetime
    chain_id: int
    signature: str
