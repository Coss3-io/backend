from adrf.views import APIView
from asgiref.sync import sync_to_async
from django.db.utils import IntegrityError
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.response import Response
from api.models import User
from api.serializers.user import UserSerializer
import api.errors as errors


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
