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
    WRONG_CHECKSUM = "the {} address you gave is not checksumed"


class KeccakHash:
    SHORT_HASH_ERROR = "the order_hash you gave is too short"
    LONG_HASH_ERROR = "the order_hash you gave is too long"
    WRONG_HASH_ERROR = "the order_hash submitted is hill formed"
    MISMATCH_HASH_ERROR = "the provided order hash does not match the computed hash"


# Order related Errors
class Order:
    ID_SUBMITTED_ERROR = "the id field must not be submitted for orders creation"
    SAME_BASE_QUOTE_ERROR = "the base_token and quote_token fields must be different"
    LOWER_BOUND_GTE_UPPER_BOUND = "the lower_bound must be smaller than the upper_bound"
    LOWER_BOUND_GT_PRICE = "the lower_bound must be smaller or equal to the price"
    PRICE_GT_UPPER_BOUND = "the price cannot be greater than the lower bound"
    BOT_EXISTING_ORDER = "this bot has already existing orders"
    TRADE_FIELD_FORMAT_ERROR = "the trades field must be a json"
    TRADE_DATA_ERROR = "the trades field do not contain valid data"
    NO_MAKER_FOUND = "no matching maker order found"
    MAKER_ALREADY_CANCELLED = "the maker order is already cancelled"
    ORDER_POSITIVE_VIOLATION = "orders cannot have numerical negative values"
    BASE_QUOTE_NEEDED = "base_token and quote_token params are needed"
    CHAIN_ID_NEEDED = "The chain_id param is needed for your request"


# Permissions Errors
class Permissions:
    WATCH_TOWER_AUTH_FAIL = "Hash verification failed."


class General:
    MISSING_FIELD = "This field is required."
    DUPLICATE_USER = "user with this address already exists."
    TOO_OLD_TIMESTAMP = "the timestamp provided is too old for logging in"
    CHECKSUM_ADDRESS_NEEDED = "a checksum address is needed to log in"
