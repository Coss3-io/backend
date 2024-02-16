from decimal import Decimal
from typing import Any
from django.db.models.expressions import CombinedExpression
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Case, CharField, DecimalField, Sum, When
from django.db.utils import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from adrf.views import APIView
from api.models import User
import api.errors as errors
from api.models.types import Address, KeccakHash
from api.utils import validate_decimal_integer
from api.views.permissions import WatchTowerPermission
from api.models.orders import Maker, Bot, Taker
from api.serializers.orders import TakerSerializer, MakerSerializer
from api.messages import WStypes
from api.consumers.websocket import WebsocketConsumer
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()


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
                    "amount": int
                    "base_fees": bool
                    "fees": int
                    "is_buyer": bool
                }
            }
        }
        ```"""

        if (trades := request.data.get("trades", {})) == {}:
            return Response(
                {"trades": [errors.General.MISSING_FIELD.format("trade")]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (block := request.data.get("block", False)):
            return Response(
                {"block": [errors.General.MISSING_FIELD.format("block")]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (taker := request.data.get("taker", False)):
            return Response(
                {"taker": [errors.General.MISSING_FIELD.format("taker")]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(trades, dict):
            return Response(
                {"trades": [errors.Order.TRADE_FIELD_FORMAT_ERROR]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            checksum_address = Address(taker)
            validate_decimal_integer(block, "block")

            if checksum_address != taker:
                raise ValidationError(errors.Address.WRONG_CHECKSUM.format(""))
        except ValidationError as e:
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)

        try:
            makers_hash_list = [KeccakHash(maker_hash) for maker_hash in trades.keys()]
        except (KeyError, ValidationError):
            return Response(
                {"error": [errors.Order.TRADE_DATA_ERROR]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        takers: Any = {}
        user = (await User.objects.aget_or_create(address=checksum_address))[0]
        makers = (
            Maker.objects.filter(order_hash__in=makers_hash_list)
            .select_related("bot", "user", "bot__user")
            .prefetch_related("takers")
            .annotate(
                address=Case(
                    When(user__isnull=False, then=F("user__address")),
                    When(bot__isnull=False, then=F("bot__user__address")),
                    output_field=CharField(),
                ),
                base_fees=Sum(
                    Case(
                        When(takers__base_fees=True, then=F("takers__fees")),
                        default=0,
                        output_field=DecimalField(),
                    )
                ),
                quote_fees=Sum(
                    Case(
                        When(takers__base_fees=False, then=F("takers__fees")),
                        default=0,
                        output_field=DecimalField(),
                    )
                ),
            )
        )
        bot_update = []
        maker_ws = {}

        async for maker in makers:
            channel = f"{str(maker.chain_id).lower()}{str(maker.base_token).lower()}{str(maker.quote_token.lower())}"
            amount = Decimal(trades[maker.order_hash]["amount"])
            try:
                temp_maker_ws = await sync_to_async(
                    lambda: MakerSerializer(maker, context={"private": True}).data
                )()
                if channel not in takers:
                    takers[channel] = []
                if channel not in maker_ws:
                    maker_ws[channel] = []

                takers[channel].append(
                    {
                        "maker_id": maker.id,
                        "block": block,
                        "amount": trades[maker.order_hash]["amount"],
                        "fees": trades[maker.order_hash]["fees"],
                        "is_buyer": trades[maker.order_hash]["is_buyer"],
                        "base_fees": trades[maker.order_hash]["base_fees"],
                        "address": user.address,
                        "maker_hash": maker.order_hash,
                        "chain_id": maker.chain_id,
                    }
                )

                if maker.bot is not None:
                    if maker.is_buyer == trades[maker.order_hash]["is_buyer"]:
                        maker.filled = F("filled") - trades[maker.order_hash]["amount"]
                        temp_maker_ws["filled"] = "{0:f}".format(
                            Decimal(temp_maker_ws["filled"])
                            - Decimal(trades[maker.order_hash]["amount"])
                        )
                        if maker.is_buyer:
                            if maker.bot.maker_fees > Decimal("2000"):
                                fees = maker.bot.maker_fees * amount / Decimal("1e18")
                            else:
                                fees = (
                                    (
                                        (
                                            maker.price * maker.bot.maker_fees
                                            + Decimal("1000")
                                        )
                                        / (Decimal("1000"))
                                        - maker.price
                                    )
                                    * amount
                                    / Decimal("1e18")
                                )
                        else:
                            if maker.bot.maker_fees > Decimal("2000"):
                                fees = maker.bot.maker_fees * amount / Decimal("1e18")
                            else:
                                fees = (
                                    (
                                        maker.price
                                        - (maker.price * Decimal("1000"))
                                        / (maker.bot.maker_fees + Decimal("1000"))
                                    )
                                    * amount
                                    / Decimal("1e18")
                                )
                    else:
                        maker.filled = F("filled") + trades[maker.order_hash]["amount"]
                        temp_maker_ws["filled"] = "{0:f}".format(
                            Decimal(temp_maker_ws["filled"])
                            + Decimal(trades[maker.order_hash]["amount"])
                        )
                        if maker.is_buyer:
                            if maker.bot.maker_fees > Decimal("2000"):
                                fees = maker.bot.maker_fees * amount / Decimal("1e18")
                            else:
                                fees = (
                                    (
                                        maker.price
                                        - (maker.price * Decimal("1000"))
                                        / (maker.bot.maker_fees + Decimal("1000"))
                                    )
                                    * amount
                                    / Decimal("1e18")
                                )
                        else:
                            if maker.bot.maker_fees > Decimal("2000"):
                                fees = maker.bot.maker_fees * amount / Decimal("1e18")
                            else:
                                fees = (
                                    (
                                        (
                                            maker.price
                                            * (maker.bot.maker_fees + Decimal("1000"))
                                        )
                                        / (Decimal("1000"))
                                        - maker.price
                                    )
                                    * amount
                                    / Decimal("1e18")
                                )
                    temp_maker_ws["bot"]["fees_earned"] = "{0:f}".format(
                        (Decimal(maker.bot.fees_earned) + Decimal(fees)).quantize(Decimal("1."))
                    )
                    maker.bot.fees_earned = F("fees_earned") + fees.quantize(
                        Decimal("1.")
                    )
                    bot_update.append(maker.bot)
                else:
                    if (
                        maker.filled + Decimal(trades[maker.order_hash]["amount"])
                        == maker.amount
                    ):
                        maker.filled = maker.amount
                        maker.status = Maker.FILLED
                        temp_maker_ws["filled"] = temp_maker_ws["amount"]
                    else:
                        maker.filled = F("filled") + trades[maker.order_hash]["amount"]
                        temp_maker_ws["filled"] = "{0:f}".format(
                            Decimal(temp_maker_ws["filled"])
                            + Decimal(trades[maker.order_hash]["amount"])
                        )
                maker_ws[channel].append(temp_maker_ws)
            except KeyError as e:
                return Response(
                    {"error": [errors.Order.TRADE_DATA_ERROR]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not takers:
            return Response(
                {"error": [errors.Order.NO_MAKER_FOUND]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        takers_serializer = TakerSerializer(data=[taker for taker_array in takers.values() for taker in taker_array], many=True)  # type: ignore
        await sync_to_async(takers_serializer.is_valid)(raise_exception=True)
        takers_serializer.save(user=user)
        if takers_serializer.instance:
            takers_serializer.instance = await takers_serializer.instance

        try:
            await Maker.objects.abulk_update(makers, ["filled", "status"])  # type: ignore
        except IntegrityError as e:
            return Response(
                {"error": [errors.Order.ORDER_POSITIVE_VIOLATION]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if bot_update:
            await Bot.objects.abulk_update(bot_update, ["fees_earned"])  # type: ignore

        for channel_name in maker_ws:
            for data in takers[channel_name]:
                del data["maker_id"]
            await channel_layer.group_send(  # type: ignore
                channel_name,
                {
                    "type": "send.json",
                    "data": {
                        WStypes.MAKERS_UPDATE: maker_ws[channel_name],
                        WStypes.NEW_TAKERS: takers[channel_name],
                    },
                },
            )

        return Response({}, status=status.HTTP_200_OK)

    async def delete(self, request):
        """Function used for maker order cancellation"""
        try:
            maker = await Maker.objects.aget(
                order_hash=request.data.get("order_hash", "")
            )
        except ObjectDoesNotExist:
            return Response(
                {"order_hash": [errors.Order.NO_MAKER_FOUND]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if maker.status == Maker.CANCELLED:
            return Response(
                {"error": [errors.Order.MAKER_ALREADY_CANCELLED]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        maker.status = Maker.CANCELLED
        await maker.asave()

        await channel_layer.group_send(  # type: ignore
            f"{str(maker.chain_id).lower()}{str(maker.base_token).lower()}{str(maker.quote_token.lower())}",
            {"type": "send.json", "data": {WStypes.DEL_MAKER: maker.order_hash}},
        )
        return Response({}, status=status.HTTP_200_OK)
