from time import time
from adrf.views import APIView
from asgiref.sync import sync_to_async
from django.db.utils import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import login
from django.conf import settings
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from api.models import User
from api.utils import (
    validate_eth_signed_message,
    validate_decimal_integer,
    validate_user,
)
from api.models.types import Address, Signature
from api.serializers.user import UserSerializer
import api.errors as errors


class UserCreateView(APIView):
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
        signature = request.data.get("signature", "")
        address = request.data.get("address", "")

        user = UserSerializer(
            data={
                "address": address,
                "signature": signature,
                "timestamp": timestamp,
            },  # type: ignore
        )
        await sync_to_async(user.is_valid)(raise_exception=True)
        try:
            await user.save()
        except IntegrityError as e:
            return Response(
                {"address": [errors.General.DUPLICATE_USER]},
                status=HTTP_400_BAD_REQUEST,
            )
        return Response({}, status=HTTP_200_OK)


class UserLogInView(APIView):
    """Class used to log the user in"""

    async def post(self, request):
        """Method used for a user to log in into the app"""

        success, result = validate_user(request, settings.LOG_IN_MESSAGE)

        if not success:
            return Response(result, status=HTTP_400_BAD_REQUEST)
        user = (await User.objects.aget_or_create(address=result))[0]
        await sync_to_async(login)(request=request, user=user)
        return Response({}, status=HTTP_200_OK)
