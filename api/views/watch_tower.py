from decimal import Decimal
from time import time
from typing import Any
from django.db.models.expressions import CombinedExpression
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Q, Case, CharField, DecimalField, Sum, Value, When
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
                base_fees=Value("0"),
                quote_fees=Value("0"),
            )
        )
        bot_update = []
        maker_ws = {}
        taker_price = ""

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

                if maker.bot is not None:
                    if maker.is_buyer == trades[maker.order_hash]["is_buyer"]:
                        maker.filled = F("filled") - trades[maker.order_hash]["amount"]
                        temp_maker_ws["filled"] = "{0:f}".format(
                            Decimal(temp_maker_ws["filled"])
                            - Decimal(trades[maker.order_hash]["amount"])
                        )
                        if maker.is_buyer:
                            taker_price = "{0:f}".format(
                                Decimal(maker.price * 1000 / (maker.bot.maker_fees + 1000)).quantize(Decimal("1."))
                            )

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
                            taker_price = "{0:f}".format(
                                Decimal(maker.price * (maker.bot.maker_fees + 1000) / 1000).quantize(Decimal("1."))
                            )

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
                        if (
                            maker.filled + Decimal(trades[maker.order_hash]["amount"])
                            == maker.amount
                        ):
                            maker.filled = maker.amount
                            maker.status = Maker.FILLED
                            temp_maker_ws["filled"] = temp_maker_ws["amount"]
                            temp_maker_ws["status"] = "FILLED"
                        else:
                            maker.filled = (
                                F("filled") + trades[maker.order_hash]["amount"]
                            )
                            temp_maker_ws["filled"] = "{0:f}".format(
                                Decimal(temp_maker_ws["filled"])
                                + Decimal(trades[maker.order_hash]["amount"])
                            )
                        if maker.is_buyer:
                            taker_price = "{0:f}".format(
                                Decimal(maker.price * 1000 / (maker.bot.maker_fees + 1000)).quantize(Decimal("1."))
                            )
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
                            taker_price = "{0:f}".format(
                                Decimal(maker.price * (maker.bot.maker_fees + 1000) / 1000).quantize(Decimal("1."))
                            )
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
                        (Decimal(maker.bot.fees_earned) + Decimal(fees)).quantize(
                            Decimal("1.")
                        )
                    )
                    maker.bot.fees_earned = F("fees_earned") + fees.quantize(
                        Decimal("1.")
                    )
                    bot_update.append(maker.bot)
                else:
                    taker_price = "{0:f}".format(maker.price)
                    if (
                        maker.filled + Decimal(trades[maker.order_hash]["amount"])
                        == maker.amount
                    ):
                        maker.filled = maker.amount
                        maker.status = Maker.FILLED
                        temp_maker_ws["filled"] = temp_maker_ws["amount"]
                        temp_maker_ws["status"] = "FILLED"
                    else:
                        maker.filled = F("filled") + trades[maker.order_hash]["amount"]
                        temp_maker_ws["filled"] = "{0:f}".format(
                            Decimal(temp_maker_ws["filled"])
                            + Decimal(trades[maker.order_hash]["amount"])
                        )

                # The base fees and the quote fees field represents the fees increment
                # Computing the exact fees amount gathered so far would be uselessly costly
                if trades[maker.order_hash]["base_fees"]:
                    temp_maker_ws["base_fees"] = "{0:f}".format(
                        Decimal(trades[maker.order_hash]["fees"])
                    )
                else:
                    temp_maker_ws["quote_fees"] = "{0:f}".format(
                        Decimal(trades[maker.order_hash]["fees"])
                    )

                maker_ws[channel].append(temp_maker_ws)
                takers[channel].append(
                    {
                        "maker_id": maker.id,
                        "block": block,
                        "amount": trades[maker.order_hash]["amount"],
                        "price": taker_price,
                        "fees": "{0:f}".format(
                            Decimal(trades[maker.order_hash]["fees"]) * 2
                        ),
                        "is_buyer": trades[maker.order_hash]["is_buyer"],
                        "base_fees": trades[maker.order_hash]["base_fees"],
                        "address": user.address,
                        "maker_hash": maker.order_hash,
                        "chain_id": maker.chain_id,
                    }
                )
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
                data["timestamp"] = int(time())
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
        """Function used for maker order or bot cancellation"""

        chain_id = ""
        if not (base_token := request.data.get("baseToken", None)):
            return Response(
                {"base_token": [errors.General.MISSING_FIELD]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            base_token = Address(base_token)

        if not (quote_token := request.data.get("quoteToken", None)):
            return Response(
                {"quote_token": [errors.General.MISSING_FIELD]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            quote_token = Address(quote_token)

        try:
            maker = await Maker.objects.aget(
                order_hash=request.data.get("orderHash", "")
            )
            chain_id = maker.chain_id
        except Maker.DoesNotExist:
            maker = None
            error = Response(
                {"order_hash": [errors.Order.NO_MAKER_FOUND]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            bot = await Bot.objects.aget(bot_hash=request.data.get("orderHash", ""))
            chain_id = bot.chain_id
        except Bot.DoesNotExist:
            bot = None
            error = Response(
                {"order_hash": [errors.Order.NO_MAKER_FOUND]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not bot and not maker:
            return error  # type: ignore

        if maker:
            if maker.status == Maker.CANCELLED:
                return Response(
                    {"error": [errors.Order.MAKER_ALREADY_CANCELLED]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            maker.status = Maker.CANCELLED
            await maker.asave()
            await channel_layer.group_send(  # type: ignore
                f"{str(chain_id).lower()}{str(base_token).lower()}{str(quote_token.lower())}",
                {"type": "send.json", "data": {WStypes.DEL_MAKERS: [maker.order_hash]}},
            )
        elif bot:
            await bot.adelete()  # type: ignore
            await channel_layer.group_send(  # type: ignore
                f"{str(chain_id).lower()}{str(base_token).lower()}{str(quote_token.lower())}",
                {"type": "send.json", "data": {WStypes.DEL_BOTS: [bot.bot_hash]}},
            )

        return Response({}, status=status.HTTP_200_OK)


class WatchTowerVerificationView(APIView):
    """The view for the watch tower to send order that can possibly be deleted"""

    permission_classes = [WatchTowerPermission]

    async def post(self, request):
        """function used to check the orders that exceed the user balances and thus have to be deleted"""

        if not (checksum_token := request.data.get("token")):
            return Response(
                {"token": [errors.General.MISSING_FIELD]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            checksum_token = Address(checksum_token)
        if not (chain_id := request.data.get("chainId")):
            return Response(
                {"chainId": [errors.General.MISSING_FIELD]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (faulty_orders := request.data.get("orders")):
            return Response(
                {"orders": [errors.General.MISSING_FIELD]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        addresses = faulty_orders.keys()
        delete_makers = []
        delete_makers_ws = []
        delete_bots = {}

        makers = Maker.objects.select_related("user", "bot", "bot__user").filter(
            Q(base_token=checksum_token) | Q(quote_token=checksum_token),
            Q(user__address__in=addresses) | Q(bot__user__address__in=addresses),
            chain_id=chain_id,
        )

        async for maker in makers:
            if maker.base_token == checksum_token:
                if maker.amount - maker.filled > Decimal(
                    faulty_orders[
                        maker.user.address if maker.user else maker.bot.user.address
                    ]
                ):
                    delete_makers_ws.append(maker)
                    if maker.bot:
                        delete_bots[maker.bot.bot_hash] = {
                            "bot": maker.bot,
                            "base_token": maker.base_token,
                            "quote_token": maker.quote_token,
                        }
                    else:
                        delete_makers.append(maker)

            else:
                if (maker.amount - maker.filled) * maker.price / Decimal(
                    "10e18"
                ) > Decimal(
                    faulty_orders[
                        maker.user.address if maker.user else maker.bot.user.address
                    ]
                ):

                    delete_makers_ws.append(maker)
                    if maker.bot:
                        delete_bots[maker.bot.bot_hash] = {
                            "bot": maker.bot,
                            "base_token": maker.base_token,
                            "quote_token": maker.quote_token,
                        }
                    else:
                        delete_makers.append(maker)
        await Maker.objects.filter(id__in=[i.id for i in delete_makers]).aupdate(
            status=Maker.CANCELLED
        )
        await Bot.objects.filter(
            id__in=[i["bot"].id for i in delete_bots.values()]
        ).adelete()

        makers_ordered = dict()
        for maker in delete_makers_ws:
            key = f"{str(maker.chain_id).lower()}{str(maker.base_token).lower()}{str(maker.quote_token.lower())}"
            if not makers_ordered.get(key, None):
                makers_ordered[key] = []
            makers_ordered[key].append(maker.order_hash)

        bots_ordered = dict()
        for entry in delete_bots.values():
            key = f"{str(entry['bot'].chain_id).lower()}{str(entry['base_token']).lower()}{str(entry['quote_token']).lower()}"
            if not bots_ordered.get(key, None):
                bots_ordered[key] = []
            bots_ordered[key].append(entry["bot"].bot_hash)

        for channel in makers_ordered:
            data = {WStypes.DEL_MAKERS: makers_ordered[channel]}
            if channel in bots_ordered:
                data.update({WStypes.DEL_BOTS: bots_ordered[channel]})
            await channel_layer.group_send(  # type: ignore
                channel,
                {
                    "type": "send.json",
                    "data": data,
                },
            )

        return Response({}, status=status.HTTP_200_OK)
