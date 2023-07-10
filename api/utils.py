from decimal import Decimal, ROUND_DOWN, InvalidOperation
from time import time
from rest_framework.validators import ValidationError
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.response import Response
from web3 import Web3
from eth_account import Account, messages
import api.errors as errors
from api.models import User
from api.models.types import Address, Signature


def validate_eth_signed_message(
    message: bytes, signature: str, address: Address
) -> bool:
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
    try:
        match = Web3.to_checksum_address(address) == Account.recover_message(
            messages.encode_defunct(message),
            signature=signature,
        )
    except Exception as e:
        if e == "Invalid signature":
            raise e
        else:
            return False
    return match


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
        raise ValidationError(errors.Decimal.FLOATTING_POINT_NUMBER_ERROR.format(name))
    return value


def validate_address(value: str, name: str):
    """Function used to validate the user submitted address like
    field

    Arguments: \n
    `value:` the user supplied address
    `name:` name of the field
    """

    return Address(value, name)

def validate_user(request, message):
    """Function used to validate a user from 
    the provided signature and address
    """

    field_errors = {}
    success = False
    if (address := request.data.get("address", "")) == "":
        field_errors["address"] = [errors.General.MISSING_FIELD]
    if (timestamp := request.data.get("timestamp", "")) == "":
        field_errors["timestamp"] = [errors.General.MISSING_FIELD]
    if (signature := request.data.get("signature", "")) == "":
        field_errors["signature"] = [errors.General.MISSING_FIELD]

    if field_errors:
        return success, field_errors

    try:
        validate_decimal_integer(timestamp, "timestamp")
        checksum_address = Address(address)
        Signature(signature)
    except ValidationError as e:
        return success, {"error": e.detail}

    if int(time()) - int(timestamp) > 5000:
        return success, {"timestamp": [errors.General.TOO_OLD_TIMESTAMP]}

    if checksum_address != address:
        return success, {"address": [errors.General.CHECKSUM_ADDRESS_NEEDED]}
    
    message = message.format(timestamp=timestamp, address=checksum_address)

    if (
        validate_eth_signed_message(
            message=message.encode(),
            signature=signature,
            address=address,
        )
        == False
    ):
        return success, {"signature": [errors.Signature.SIGNATURE_MISMATCH_ERROR]}
    return True, checksum_address
