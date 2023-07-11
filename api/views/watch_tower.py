from typing import Any
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from adrf.views import APIView
from api.models import User
import api.errors as errors
from api.models.types import Address
from api.utils import validate_decimal_integer
from api.views.permissions import WatchTowerPermission
from api.models.orders import Maker
from api.serializers.orders import TakerSerializer


class WatchTowerView(APIView):
    """The view for the watch tower to commit order changes"""

    permission_classes = [WatchTowerPermission]

    async def post(self, request):
        """Function used to update several orders at once\n

        The data sent by the watch tower to the view is like this: \n
        ```python
        request.data = {
            "taker": "0xaddress...",
            "block": int,
            "trades":{
                "0xorderHash1...": {
                    "taker_amount": int
                    "base_fees": bool
                    "fees": int
                    "is_buyer": bool
                }
            }
        }
        ```"""
        if (trades := request.data.get("trades", {})) == {}:
            return Response(
                {"trade": [errors.General.MISSING_FIELD.format("trade")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if not (block := request.data.get("block", False)):
            return Response(
                {"block": [errors.General.MISSING_FIELD.format("block")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if not isinstance(trades, dict):
            return Response(
                {"trades": [errors.Order.TRADE_FIELD_FORMAT_ERROR]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            checksum_address = Address(request.data.get("taker", ""))
            validate_decimal_integer(block, "block")
        except ValidationError as e:
            return Response({"error": e.detail})

        try:
            makers_hash_list = [maker_hash for maker_hash in trades.keys()]
        except KeyError:
            return Response(
                {"detail": "the trade field is not correctly formed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        takers: Any = []
        user = User.objects.aget_or_create(address=checksum_address)
        makers = Maker.objects.filter(order_hash__in=[makers_hash_list])

        async for maker in makers:
            takers.append(
                {
                    "maker": maker,
                    "block": block,
                    "taker_amount": trades[maker.order_hash]["taker_amount"],
                    "fees": trades[maker.order_hash]["fees"],
                    "is_buyer": trades[maker.order_hash]["is_buyer"],
                    "base_fees": trades[maker.order_hash]["base_fees"],
                }
            )

        takers_serializer = TakerSerializer(data=takers, many=True)
        await sync_to_async(takers_serializer.is_valid)(raise_exception=True)
        takers_serializer.save(user=(await user)[0])
        if takers_serializer.instance:
            await takers_serializer.instance
        return Response({}, status=status.HTTP_200_OK)

    async def delete(self, request):
        """Function used for maker order cancellation"""
        try:
            maker = Maker.objects.get(order_hash=request.data.get("order_hash", ""))
        except ObjectDoesNotExist:
            return Response(
                {"data": "order_hash field is wrong"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        maker.status = Maker.CANCELLED
        await maker.asave()
        return Response({}, status=status.HTTP_200_OK)
