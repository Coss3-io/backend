from eth_account import Account
from api.models.types import Address
from web3 import Web3


def validate_eth_signed_message(message: str, signature: str, address: Address) -> bool:
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
        f'"\x19Ethereum Signed Message:\n32"{message}',
        signature=signature,
    )
