from typing import Any
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from adrf.views import APIView
from api.models import User
from api.models.orders import Maker
from api.serializers.orders import TakerSerializer


class WatchTowerview(APIView):
    """The view for the watch tower to commit order changes"""

    authentication_classes = []  # custom authentication here

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
        trades = request.data.get("trades", {})
        block = request.data.get("block", 0)

        if trades == {}:
            return Response(
                {"detail": "the trade field cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(trades, dict):
            return Response(
                {"detail": "the trade field must be json"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if block == 0:
            return Response(
                {"detail": "the block field is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            makers_hash_list = [maker_hash for maker_hash in trades.keys()]
        except KeyError:
            return Response(
                {"detail": "the trade field is not correctly formed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        takers: Any = []
        user = User.objects.aget_or_create(address=request.data["taker"])
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

    async def delete(self, request):
        """Function used for order cancellation"""
