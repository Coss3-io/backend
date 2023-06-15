from typing import TypedDict, Any
from decimal import Decimal
from datetime import date
from rest_framework.validators import ValidationError


class Address(str):
    def __new__(cls, value, name="address"):
        if len(value) > 42:
            raise ValidationError(f"the {name} you gave is too long")
        try:
            int(value, 0)
        except ValueError:
            raise ValidationError(f"the {name} submitted is hill formed")
        return super().__new__(cls, value)
    
class Signature(str):
    def __new__(cls, value):
        if len(value) > 132:
            raise ValidationError("the signature you gave is too long")
        try:
            int(value, 0)
        except ValueError:
            raise ValidationError("the signature submitted is hill formed")
        return super().__new__(cls, value)
    
class KeccakHash(str):
    def __new__(cls, value):
        if len(value) > 66:
            raise ValidationError("the hash you gave is too long")
        try:
            int(value, 0)
        except ValueError:
            raise ValidationError("the hash submitted is hill formed")
        return super().__new__(cls, value)
    


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
