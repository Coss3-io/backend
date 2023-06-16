from decimal import Decimal, ROUND_DOWN, InvalidOperation
import api.errors as errors
from rest_framework.validators import ValidationError
from eth_account import Account, messages
from api.models.types import Address
from web3 import Web3


def validate_eth_signed_message(
    """Function used to validate an eth signed message

    Arguments :\n
    `message`   -- The message that has been signed\n
    `signature` -- The signature sent by the user\n
    `address`   -- The address claiming to have signed the message\n
    Usage :
    ```python
    message = "Log in to coss3.io"
    signature = "0x123..."
    address = "0xab123..."
    result = validate_eth_signed_message(message=message, signature=signature, address=address)
    ```
    """

    return Web3.to_checksum_address(address) == Account.recover_message(
        messages.encode_defunct(message),
        signature=signature,
    )


def validate_decimal_integer(value: str, name: str):
    """Function used to validate the user decimal numbers
    raise a validation error on wrong input

    Arguments: \n
    `value:` the user supplied number
    `name:` name of the field
    """
    try:
        decimal_value = Decimal(value)
    except InvalidOperation:
        raise ValidationError(errors.Decimal.WRONG_DECIMAL_ERROR.format(name))
    if decimal_value == Decimal("0"):
        raise ValidationError(errors.Decimal.ZERO_DECIMAL_ERROR.format(name))

    if decimal_value != Decimal(value).quantize(Decimal("1."), rounding=ROUND_DOWN):
        raise ValidationError(f"the {name} must be a integer number")
    return value

def validate_address(value: str, name: str):
    """Function used to validate the user submitted address like
    field

    Arguments: \n
    `value:` the user supplied address
    `name:` name of the field
    """

    return Address(value, name)