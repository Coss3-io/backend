# User view error messages
class User:
    USER_TIMESTAMP_ERROR = "The submitted timestamp for account creation is too old"


# Signature Related Errors
class Signature:
    SIGNATURE_MISMATCH_ERROR = "The signature provided does not match the address"
    SHORT_SIGNATURE_ERROR = "the signature you gave is too short"
    LONG_SIGNATURE_ERROR = "the signature you gave is too long"
    WRONG_SIGNATURE_ERROR = "the signature submitted is hill formed"


# Number related Errors
class Decimal:
    ZERO_DECIMAL_ERROR = "the {} submitted cannot be zero"
    WRONG_DECIMAL_ERROR = "the {} submitted is not a number"
    FLOATTING_POINT_NUMBER_ERROR = "the {} must be a integer number"


class Address:
    SHORT_ADDRESS_ERROR = "the {} address you gave is too short"
    LONG_ADDRESS_ERROR = "the {} address you gave is too long"
    WRONG_ADDRESS_ERROR = "the {} address submitted is hill formed"


class KeccakHash:
    SHORT_HASH_ERROR = "the order_hash you gave is too short"
    LONG_HASH_ERROR = "the order_hash you gave is too long"
    WRONG_HASH_ERROR = "the order_hash submitted is hill formed"

# Order related Errors
class Order:
    ID_SUBMITTED_ERROR = "the id field must not be submitted for orders creation"

# Permissions Errors
class Permissions:
    WATCH_TOWER_AUTH_FAIL = 'Hash verification failed.'

class General:
    MISSING_FIELD = "This field is required."
