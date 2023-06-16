from time import time
from adrf.views import APIView
from asgiref.sync import sync_to_async
from rest_framework.status import HTTP_200_OK
from rest_framework.response import Response
from api.models import User
from api.utils import validate_decimal_integer
from api.models.types import Signature, Address
from api.serializers.user import UserSerializer


class UserView(APIView):
    """View for user creation"""

    def get_queryset(self):
        return User.objects.all()

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

        timestamp = request.data.get("timestamp", 0)
        signature = Signature(request.data.get("signature", ""))
        address = Address(request.data.get("address", ""))

        user = UserSerializer(
            data={"address": address},  # type: ignore
            context={
                "signature": signature,
                "timestamp": timestamp,
            },
        )
        await sync_to_async(user.is_valid)(raise_exception=True)
        await user.save()
        return Response({}, status=HTTP_200_OK)
