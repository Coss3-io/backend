# User view error messages
class User:
    USER_TIMESTAMP_ERROR = "The submitted timestamp for account creation is too old"

# Signature Related Errors
class Signature:
    SIGNATURE_MISMATCH_ERROR = "The signature provided does not match the address"

# Number related Errors 
class Decimal:
    ZERO_DECIMAL_ERROR = "the {} submitted cannot be zero"
    WRONG_DECIMAL_ERROR = "the {} submitted is not a number"
    FLOATTING_POINT_NUMBER_ERROR = "the {} must be a integer number"

class Address:
    SHORT_ADDRESS_ERROR = "the {} address you gave is too short"
    LONG_ADDRESS_ERROR = "the {} address you gave is too long"
    WRONG_ADDRESS_ERROR = "the {} address submitted is hill formed"