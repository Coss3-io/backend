from time import time
from adrf.views import APIView
from rest_framework.exceptions import APIException
from rest_framework.status import HTTP_200_OK
from rest_framework.response import Response
from api.models import User
from api.utils import validate_decimal_integer, validate_eth_signed_message
from api.models.types import Signature, Address


class UserView(APIView):
    """View for user creation"""

    async def post(self, request):
        """View for user creation

        ```python
        request.data = {
            "address": "0xaddress..."
            "signature": "0xsignature..."
            "timestamp": 120
        }
        ```
        """

        timestamp = validate_decimal_integer(request.get("timestamp", 0), "timestamp")
        signature = Signature(request.data.get("signature", ""))
        address = Address(request.data.get("address", ""))

        if not validate_eth_signed_message(
            message=f"account creation to coss3.io on {timestamp}".encode(),
            signature=signature,
            address=address,
        ):
            raise APIException("wrong signature provided for account creation")
        await User.objects.create_user(address=address)

        return Response({}, status=HTTP_200_OK)
