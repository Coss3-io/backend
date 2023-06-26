from asgiref.sync import sync_to_async
from django.db.models import F
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from adrf.views import APIView
from api.models import User
from api.models.stacking import Stacking, StakingFees
from api.views.permissions import WatchTowerPermission
from api.serializers.stacking import StackingSerializer, StackingFeesSerializer
from api.models.types import Address
import api.errors as errors
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
        data = await sync_to_async(
            lambda: StackingSerializer(stackings, many=True).data
        )()
        return Response(data, status=status.HTTP_200_OK)

    @permission_classes([WatchTowerPermission])
    async def post(self, request):
        """Allows the watch tower to publish new stacking entries

        The data sent by the watch tower has to be like this:
        ```python
        request.data = {
            "address": "0x123...",
            "amount": int,
            "slot": int,
        }
        ```"""

        stacking = StackingSerializer(data=request.data)
        await sync_to_async(stacking.is_valid)(raise_exception=True)

        if not isinstance(stacking.validated_data, dict):
            # never happens
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        user = (
            await User.objects.aget_or_create(
                address=stacking.validated_data["address"]
            )
        )[0]
        stacking.save(user=user)

        if stacking.instance:
            stacking.instance = await stacking.instance
            stacking.instance.amount = stacking.validated_data["amount"]
            await stacking.instance.asave(update_fields=["amount"])
            stacking.validated_data["amount"] = stacking.data["amount"]
            return Response(
                {},
                status=status.HTTP_200_OK,
            )
        else:
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

    @permission_classes([WatchTowerPermission])
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
            # raise APIException("address can't be empty")

        amount = validate_decimal_integer(request.data.get("amount", "0"), "amount")
        slot = validate_decimal_integer(request.data.get("slot", "0"), "slot")

        stacking_fees = (await Stacking.objects.aget_or_create(token=token, slot=slot))[
            0
        ]

        stacking_fees.amount = F("amount") + amount
        await stacking_fees.asave(update_fields=["amount"])
        return Response({}, status=status.HTTP_200_OK)
