from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import APIException
from adrf.views import APIView
from asgiref.sync import sync_to_async
from api.models import User
from api.models.stacking import Stacking, StakingFees
from api.serializers.stacking import StackingSerializer, StackingFeesSerializer
from api.models.types import Address
from api.utils import validate_decimal_integer


class StackingView(APIView):
    """Class used for retrieve stacking informations"""

    def get_permissions(self):
        data = super().get_permissions()
        return data + [permission() for permission in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "permission_classes", [])]  # type: ignore


    @permission_classes([IsAuthenticated])
    async def get(self, request: Request):
        """Retrieves a user stacking amount per block"""

        stackings = Stacking.objects.filter(user=request.user)
        stackings = StackingSerializer(stackings, many=True)
        return Response(stackings.data, status=status.HTTP_200_OK)

    @permission_classes([])
    async def post(self, request):
        """Allows the watch tower to publish new stacking entries

        The data sent by the watch tower has to be like this:
        ```python
        request.data = {
            "address": "0x123...",
            "amount": int,
            "token": "0xabc...",
            "slot": int,
        }
        ```"""

        if address := request.data.get("address", "") == "":
            Address(address)
            raise APIException("address can't be empty")

        if token := request.data.get("token", "") == "":
            Address(token, "token")
            raise APIException("address can't be empty")

        amount = validate_decimal_integer(request.data.get("amount", "0"), "amount")
        slot = validate_decimal_integer(request.data.get("slot", "0"), "slot")

        user = await User.objects.aget_or_create(address=request.data.get("address"))
        stacking = (
            await Stacking.objects.aget_or_create(user=user, token=token, slot=slot)
        )[0]

        stacking.amount = F("amount") + amount
        await stacking.asave(update_fields=["amount"])
        return Response({}, status=status.HTTP_200_OK)


class StackingFeesView(APIView):
    """View used to update the fees entries per token per slot"""

    def get_permissions(self):
        data = super().get_permissions()
        return data + [permission() for permission in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "permission_classes", [])]  # type: ignore


    async def get(self, request):
        """Used to get the fees entries for all the slots since the creation of the app"""

        stacking_fees = StakingFees.objects.all()
        data = StackingFeesSerializer(stacking_fees, many=True)
        return Response(data, status=status.HTTP_200_OK)

    @permission_classes([])
    async def post(self, request):
        """Used by the watch tower to commit new stacking fees entries

        data received:

        ```python
        request.data = {
            "slot": int,
            "token": "0xadddress....",
            "amount": int
        }
        ```"""

        if token := request.data.get("token", "") == "":
            Address(token, "token")
            raise APIException("address can't be empty")

        amount = validate_decimal_integer(request.data.get("amount", "0"), "amount")
        slot = validate_decimal_integer(request.data.get("slot", "0"), "slot")

        stacking_fees = (await Stacking.objects.aget_or_create(token=token, slot=slot))[
            0
        ]

        stacking_fees.amount = F("amount") + amount
        await stacking_fees.asave(update_fields=["amount"])
        return Response({}, status=status.HTTP_200_OK)
