from typing import TypedDict, Any
from decimal import Decimal
from datetime import date


class Address(str):
    def __new__(cls, value):
        if len(value) > 42:
            raise ValueError("The address you gave is more too long")
        try:
            int(value, 0)
        except ValueError:
            raise ValueError("The address submitted is hill formed")
        return cls.__init__(value)


class MakerTypedDict(TypedDict):
    owner: Any
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
