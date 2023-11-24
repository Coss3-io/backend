from asgiref.sync import sync_to_async
from django.db.models import F
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from adrf.views import APIView
from api.models import User
from api.models.stacking import Stacking, StackingFees
from api.views.permissions import WatchTowerPermission
from api.serializers.stacking import StackingSerializer, StackingFeesSerializer
from api.messages import WStypes
from api.consumers.websocket import WebsocketConsumer
from api.views.authentications import ApiAuthentication
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()


class StackingView(APIView):
    """Class used for retrieve stacking informations"""

    def get_authenticators(self):
        data = super().get_authenticators()
        return data + [auth() for auth in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "authentication_classes", [])]  # type: ignore

    def get_permissions(self):
        data = super().get_permissions()
        return data + [permission() for permission in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "permission_classes", [])]  # type: ignore

    @authentication_classes([ApiAuthentication, SessionAuthentication])
    @permission_classes([IsAuthenticated])
    async def get(self, request: Request):
        """Retrieves a user stacking amount per block"""

        if request.auth == "awaitable":
            request.user = (await User.objects.aget_or_create(address=request.user))[0]

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

            await channel_layer.group_send(  # type: ignore
                WebsocketConsumer.groups[0],
                {"type": "send.json", "data": {WStypes.NEW_STACKING: stacking.validated_data}},
            )

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

        queryset = StackingFees.objects.all()
        data = await sync_to_async(
            lambda: StackingFeesSerializer(queryset, many=True).data
        )()
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

        stacking_fees = StackingFeesSerializer(data=request.data)
        await sync_to_async(stacking_fees.is_valid)(raise_exception=True)

        if not isinstance(stacking_fees.validated_data, dict):
            # never happens
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        stacking_fees.save()

        if stacking_fees.instance:
            stacking_fees.instance = await stacking_fees.instance
            stacking_fees.instance.amount = stacking_fees.validated_data["amount"]
            await stacking_fees.instance.asave(update_fields=["amount"])
            stacking_fees.validated_data["amount"] = stacking_fees.data["amount"]

            await channel_layer.group_send(  # type: ignore
                WebsocketConsumer.groups[0],
                {"type": "send.json", "data": {WStypes.NEW_FEES: stacking_fees.validated_data}},
            )

            return Response(
                {},
                status=status.HTTP_200_OK,
            )
        else:
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
