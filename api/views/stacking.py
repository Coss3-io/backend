from asgiref.sync import sync_to_async, async_to_sync
from django.db.models import F, Sum
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from adrf.views import APIView
from api.models import User
from api.models.stacking import Stacking, StackingFees, StackingFeesWithdrawal
from api.views.permissions import WatchTowerPermission
from api.serializers.stacking import (
    StackingSerializer,
    StackingFeesSerializer,
    StackingFeesWithdrawalSerializer,
)
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

        stackings = Stacking.objects.filter(user=request.user).order_by("slot")
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
            "withdraw": bool
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
            amount = stacking.validated_data["amount"] * (
                -1 if stacking.validated_data["withdraw"] else 1
            )

            stacking.instance.amount = F("amount") + amount
            await stacking.instance.asave(update_fields=["amount"])
            stacking.validated_data["amount"] = "{0:f}".format(amount)

            await channel_layer.group_send(  # type: ignore
                WebsocketConsumer.groups[0],
                {
                    "type": "send.json",
                    "data": {WStypes.NEW_STACKING: stacking.validated_data},
                },
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

    @sync_to_async
    @method_decorator(cache_page(60 * 60 * 24))
    @async_to_sync
    async def get(self, request):
        """Used to get the fees entries for all the slots since the creation of the app"""

        queryset = StackingFees.objects.all().order_by("slot")
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
                {
                    "type": "send.json",
                    "data": {WStypes.NEW_FEES: stacking_fees.validated_data},
                },
            )

            return Response(
                {},
                status=status.HTTP_200_OK,
            )
        else:
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StackingFeesWithdrawalView(APIView):
    """View used to update the fees withdrawal entries per token per slot"""

    def get_authenticators(self):
        data = super().get_authenticators()
        return data + [auth() for auth in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "authentication_classes", [])]  # type: ignore

    def get_permissions(self):
        data = super().get_permissions()
        return data + [permission() for permission in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "permission_classes", [])]  # type: ignore

    @authentication_classes([ApiAuthentication, SessionAuthentication])
    @permission_classes([IsAuthenticated])
    async def get(self, request):
        """Function used to retrieve the fees withdrawn by the user"""

        if request.auth == "awaitable":
            request.user = (await User.objects.aget_or_create(address=request.user))[0]

        stackings = StackingFeesWithdrawal.objects.filter(user=request.user).order_by("slot")
        data = await sync_to_async(
            lambda: StackingFeesWithdrawalSerializer(stackings, many=True).data
        )()
        return Response(data, status=status.HTTP_200_OK)

    @permission_classes([WatchTowerPermission])
    async def post(self, request):
        """Used by the watch tower to commit new stackingFees withdrawal entries

        data received:

        ```python
        request.data = {
            "slot": int,
            "token": "0xadddress....",
            "address": "0xadddress....",
        }
        ```"""

        stacking_fees_withdrawal = StackingFeesWithdrawalSerializer(data=request.data)
        await sync_to_async(stacking_fees_withdrawal.is_valid)(raise_exception=True)

        if not isinstance(stacking_fees_withdrawal.validated_data, dict):
            # never happens
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        user = (
            await User.objects.aget_or_create(
                address=stacking_fees_withdrawal.validated_data["address"]
            )
        )[0]
        stacking_fees_withdrawal.save(user=user)

        if stacking_fees_withdrawal.instance:
            stacking_fees_withdrawal.instance = await stacking_fees_withdrawal.instance

            await channel_layer.group_send(  # type: ignore
                WebsocketConsumer.groups[0],
                {
                    "type": "send.json",
                    "data": {
                        WStypes.NEW_FSA_WITHDRAWAL: stacking_fees_withdrawal.validated_data
                    },
                },
            )

            return Response(
                {},
                status=status.HTTP_200_OK,
            )
        else:
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GlobalStackingView(APIView):
    """View used to retrieve the global staking amount for all the users"""

    @sync_to_async
    @method_decorator(cache_page(60 * 60 * 24))
    @async_to_sync
    async def get(self, request):
        """Retrieves the global stacking amount"""

        stacks = (
            Stacking.objects.values_list("slot")
            .annotate(amount=Sum("amount"))
            .order_by("slot")
        )
        return Response(stacks, status=status.HTTP_200_OK)
