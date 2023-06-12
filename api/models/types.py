from typing import TypedDict, Any
from decimal import Decimal
from datetime import date
from rest_framework.exceptions import APIException


class Address(str):
    def __new__(cls, value):
        if len(value) > 42:
            raise APIException("the address you gave is too long")
        try:
            int(value, 0)
        except ValueError:
            raise APIException("the address submitted is hill formed")
        return cls.__init__(value)
    
class Signature(str):
    def __new__(cls, value):
        if len(value) > 132:
            raise APIException("the signature you gave is too long")
        try:
            int(value, 0)
        except ValueError:
            raise APIException("the signature submitted is hill formed")
        return cls.__init__(value)
    
class KeccakHash(str):
    def __new__(cls, value):
        if len(value) > 66:
            raise APIException("the hash you gave is too long")
        try:
            int(value, 0)
        except ValueError:
            raise APIException("the hash submitted is hill formed")
        return cls.__init__(value)


class MakerTypedDict(TypedDict):
    user: Any
    base_token: Address
    quote_token: Address
    amount: Decimal
    price: Decimal
    filled: Decimal
    is_buyer: bool
    expiry: date
    status: str
    order_hash: str
    signature: str

class UserTypedDict(TypedDict):
    address: Address
    is_admin: bool
    is_active: bool

class BotTypedDict(TypedDict):
    step: Decimal
    price: Decimal
    maker_fees: Decimal
    upper_bound: Decimal
    lower_bound: Decimal
    fees_earned: Decimal
