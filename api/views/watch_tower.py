from decimal import Decimal
from typing import Any
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from adrf.views import APIView
from api.models import User
import api.errors as errors
from api.models.types import Address
from api.utils import validate_decimal_integer, compute_order_hash
from api.views.permissions import WatchTowerPermission
from api.models.orders import Maker, Bot
from api.serializers.orders import TakerSerializer, MakerSerializer


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

        if not makers_hash_list:
            pass # add an error for non existent maker hashes

        takers: Any = []
        user = User.objects.aget_or_create(address=checksum_address)
        makers = Maker.objects.filter(order_hash__in=makers_hash_list).select_related(
            "bot"
        )
        bot_update = []

        async for maker in makers:
            takers.append(
                {
                    "maker_id": maker.id,
                    "block": block,
                    "taker_amount": trades[maker.order_hash]["taker_amount"],
                    "fees": trades[maker.order_hash]["fees"],
                    "is_buyer": trades[maker.order_hash]["is_buyer"],
                    "base_fees": trades[maker.order_hash]["base_fees"],
                }
            )
            

            if maker.bot is not None:
                if maker.is_buyer == trades[maker.order_hash]["is_buyer"]:
                    maker.filled = (
                        F("filled") - trades[maker.order_hash]["taker_amount"]
                    )
                    if maker.is_buyer:
                        if maker.bot.maker_fees > Decimal("2000"):
                            fees = maker.bot.maker_fees * maker.amount
                        else:
                            fees = (
                                (maker.price * maker.bot.maker_fees + Decimal("1000"))
                                / (Decimal("1000"))
                                - maker.price
                            ) * maker.amount
                    else:
                        if maker.bot.maker_fees > Decimal("2000"):
                            fees = maker.bot.maker_fees * maker.amount
                        else:
                            fees = (
                                maker.price
                                - (maker.price * Decimal("1000"))
                                / (maker.bot.maker_fees + Decimal("1000"))
                            ) * maker.amount
                else:
                    maker.filled = (
                        F("filled") + trades[maker.order_hash]["taker_amount"]
                    )
                    if maker.is_buyer:
                        if maker.bot.maker_fees > Decimal("2000"):
                            fees = maker.bot.maker_fees * maker.amount
                        else:
                            fees = (
                                maker.price
                                - (maker.price * Decimal("1000"))
                                / (maker.bot.maker_fees + Decimal("1000"))
                            ) * maker.amount
                    else:
                        if maker.bot.maker_fees > Decimal("2000"):
                            fees = maker.bot.maker_fees * maker.amount
                        else:
                            fees = (
                                (maker.price * maker.bot.maker_fees + Decimal("1000"))
                                / (Decimal("1000"))
                                - maker.price
                            ) * maker.amount
                            
                maker.bot.fees_earned = F("fees_earned") + fees
                bot_update.append(maker.bot)
            else:
                if (
                    maker.filled + Decimal(trades[maker.order_hash]["taker_amount"])
                    == maker.amount
                ):
                    maker.filled = maker.amount
                    maker.status = Maker.FILLED
                else:
                    maker.filled = F("filled") + trades[maker.order_hash]["taker_amount"]

        takers_serializer = TakerSerializer(data=takers, many=True)
        await sync_to_async(takers_serializer.is_valid)(raise_exception=True)
        takers_serializer.save(user=(await user)[0])
        if takers_serializer.instance:
            await takers_serializer.instance
        await Maker.objects.abulk_update(makers, ["filled", "status"]) #type: ignore

        if bot_update:
            await Bot.objects.abulk_update(bot_update, ["fees_earned"]) #type: ignore
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
