from asyncio import gather
from decimal import Decimal
from asgiref.sync import sync_to_async
from adrf.views import APIView
from django.db.models import Q
from django.db.utils import IntegrityError
from rest_framework import status
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from api.models.orders import Maker, Bot, Taker
from api.models.types import Address
from api.models import User
import api.errors as errors
from api.serializers.orders import MakerSerializer, BotSerializer, TakerSerializer
from api.utils import validate_chain_id
from api.views.authentications import ApiAuthentication
from api.messages import WStypes
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()


class OrderView(APIView):
    """View used to retrieve the orders to populate the order books"""

    async def get(self, request: Request):
        """Function used to get all the orders for a given pair"""

        if (base_token := request.query_params.get("base_token", "0")) == "0" or (
            quote_token := request.query_params.get("quote_token", "0")
        ) == "0":
            return Response(
                {"detail": errors.Order.BASE_QUOTE_NEEDED},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            base_token = Address(base_token, "base_token")
        except ValidationError as e:
            raise ValidationError({"base_token": e.detail})

        try:
            quote_token = Address(quote_token, "quote_token")
        except ValidationError as e:
            raise ValidationError({"quote_token": e.detail})

        queryset = (
            Maker.objects.filter(
                base_token=base_token,
                quote_token=quote_token,
                chain_id=validate_chain_id(request.query_params.get("chain_id", None)),
            )
            .select_related("user", "bot", "bot__user")
            .prefetch_related("takers")
        )
        length = await sync_to_async(len)(queryset)
        if length:
            await sync_to_async(queryset[0].takers.all)()
        data = await sync_to_async(lambda: MakerSerializer(queryset, many=True).data)()
        return Response(data, status=status.HTTP_200_OK)


class MakerView(APIView):
    """The views user to retrieve and create Maker Orders"""

    def get_authenticators(self):
        data = super().get_authenticators()
        return data + [auth() for auth in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "authentication_classes", [])]  # type: ignore

    def get_permissions(self):
        data = super().get_permissions()
        return data + [permission() for permission in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "permission_classes", [])]  # type: ignore

    @authentication_classes([ApiAuthentication, SessionAuthentication])
    @permission_classes([IsAuthenticated])
    async def get(self, request: Request):
        """The view to retrieve the orders of a user"""

        if request.auth == "awaitable":
            request.user = (await User.objects.aget_or_create(address=request.user))[0]
        chain_id = validate_chain_id(request.query_params.get("chain_id", None))

        if request.query_params.get("all", None):
            queryset = (
                Maker.objects.filter(chain_id=chain_id)
                .select_related("user")
                .prefetch_related("takers")
            )
        else:
            if (base_token := request.query_params.get("base_token", "0")) == "0" or (
                quote_token := request.query_params.get("quote_token", "0")
            ) == "0":
                return Response(
                    {"detail": "base_token and quote_token params are needed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                base_token = Address(base_token, "base_token")
            except ValidationError as e:
                raise ValidationError({"base_token": e.detail})
            try:
                quote_token = Address(quote_token, "quote_token")
            except ValidationError as e:
                raise ValidationError({"quote_token": e.detail})

            queryset = Maker.objects.filter(
                base_token=base_token,
                quote_token=quote_token,
                chain_id=chain_id,
            ).prefetch_related("takers")

        queryset = queryset.filter(
            Q(user=request.user) | Q(bot__user=request.user),
        )
        length = await sync_to_async(len)(queryset)
        if length:
            await sync_to_async(queryset[0].takers.all)()
        data = await sync_to_async(lambda: MakerSerializer(queryset, many=True).data)()
        return Response(data, status=status.HTTP_200_OK)

    async def post(self, request):
        """The method used to create a maker order"""

        maker = MakerSerializer(data=request.data)
        await sync_to_async(maker.is_valid)(raise_exception=True)
        maker.save(filled=Decimal("0"))

        if maker.instance is not None:
            maker.instance = await maker.instance
        data = await sync_to_async(lambda: maker.data)()

        await channel_layer.group_send(  # type: ignore
            f"{str(data['chain_id']).lower()}{str(data['base_token']).lower()}{data['quote_token'].lower()}",
            {"type": "send.json", "data": {WStypes.NEW_MAKER: data}},
        )

        return Response(data, status=status.HTTP_200_OK)


class TakerView(APIView):
    """View used to retrieve the logged in users taker orders"""

    authentication_classes = [ApiAuthentication, SessionAuthentication]

    async def get(self, request):
        """Function used to retrieve the user taker orders"""

        if request.auth == "awaitable":
            request.user = (await User.objects.aget_or_create(address=request.user))[0]
        chain_id = validate_chain_id(request.query_params.get("chain_id", None))
        if request.query_params.get("all", None):
            queryset = Taker.objects.filter(maker__chain_id=chain_id)
        else:
            if (base_token := request.query_params.get("base_token", "0")) == "0" or (
                quote_token := request.query_params.get("quote_token", "0")
            ) == "0":
                return Response(
                    {"detail": errors.Order.BASE_QUOTE_NEEDED},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                base_token = Address(base_token, "base_token")
            except ValidationError as e:
                raise ValidationError({"base_token": e.detail})
            try:
                quote_token = Address(quote_token, "quote_token")
            except ValidationError as e:
                raise ValidationError({"quote_token": e.detail})

            queryset = Taker.objects.filter(
                maker__chain_id=chain_id,
                maker__base_token=base_token,
                maker__quote_token=quote_token,
            )

            if request.user.id:
                queryset = queryset.filter(user=request.user)
            queryset = queryset.order_by("-timestamp").select_related("maker")

        data = await sync_to_async(lambda: TakerSerializer(queryset, many=True).data)()
        return Response(data, status=status.HTTP_200_OK)


class BatchUserOrdersView(APIView):
    """View used by the front end to get all of the orders and users orders at once"""

    authentication_classes = [ApiAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    async def get(self, request):
        """wrapper function to gather all the data from all the orders"""

        if request.auth == "awaitable":
            request.user = (await User.objects.aget_or_create(address=request.user))[0]
            request.auth = None
        user_id = request.user.id
        request.user.id = None

        takers = TakerView.as_view()(request._request)
        request.user.id = user_id
        user_takers = TakerView.as_view()(request._request)
        makers = OrderView.as_view()(request._request)
        user_makers = MakerView.as_view()(request._request)
        takers, user_takers, makers, user_makers = await gather(takers, user_takers, makers, user_makers)  # type: ignore
        data = {
            "takers": takers.data,
            "user_takers": user_takers.data,
            "makers": makers.data,
            "user_makers": user_makers.data,
        }
        return Response(
            data,
            status=status.HTTP_200_OK,
        )


class BotView(APIView):
    """View used to create and retrieve bots"""

    def get_authenticators(self):
        data = super().get_authenticators()
        return data + [auth() for auth in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "authentication_classes", [])]  # type: ignore

    def get_permissions(self):
        data = super().get_permissions()
        return data + [permission() for permission in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "permission_classes", [])]  # type: ignore

    @authentication_classes([ApiAuthentication, SessionAuthentication])
    @permission_classes([IsAuthenticated])
    async def get(self, request):
        """Returns the user bots list,"""
        if request.auth == "awaitable":
            request.user = (await User.objects.aget_or_create(address=request.user))[0]
        chain_id = validate_chain_id(request.query_params.get("chain_id", None))

        bots = (
            Bot.objects.filter(user=request.user, chain_id=chain_id)
            .select_related("user")
            .prefetch_related("orders")
        )
        data = await sync_to_async(lambda: BotSerializer(bots, many=True).data)()
        return Response(data, status=status.HTTP_200_OK)

    async def post(self, request):
        """View used to create a new bot"""

        bot = BotSerializer(data=request.data)
        await sync_to_async(bot.is_valid)(raise_exception=True)
        bot.save()

        try:
            if bot.instance is not None:
                bot.instance = await bot.instance
        except IntegrityError as e:
            return Response(
                {"error": [errors.Order.BOT_EXISTING_ORDER]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = await sync_to_async(lambda: bot.data)()

        await channel_layer.group_send(  # type: ignore
            f"{str(data['chain_id']).lower()}{str(data['base_token']).lower()}{data['quote_token'].lower()}",
            {"type": "send.json", "data": {WStypes.NEW_BOT: data}},
        )

        return Response(data, status=status.HTTP_200_OK)
