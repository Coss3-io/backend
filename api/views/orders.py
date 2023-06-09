from decimal import Decimal
from datetime import datetime
from asgiref.sync import sync_to_async
from adrf.views import APIView
from django.db.utils import IntegrityError
from rest_framework import status
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from api.models.orders import Maker, Bot
from api.models.types import Address
from api.models import User
import api.errors as errors
from api.serializers.orders import MakerSerializer, BotSerializer
from api.views.authentications import ApiAuthentication


class OrderView(APIView):
    """View used to retrieve the orders to populate the order books"""

    async def get(self, request: Request):
        """Function used to get all the orders for a given pair"""

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
            base_token=base_token, quote_token=quote_token
        ).select_related("user", "bot", "bot__user")
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

    @authentication_classes([ApiAuthentication])
    @permission_classes([IsAuthenticated])
    async def get(self, request: Request):
        """The view to retrieve the orders of a user"""
        
        if request.auth == "awaitable":
            request.user = (await User.objects.aget_or_create(address=request.user))[0]

        if request.query_params.get("all", None):
            queryset = Maker.objects.filter(user=request.user).select_related("user")
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
                user=request.user, base_token=base_token, quote_token=quote_token
            )
        data = await sync_to_async(lambda: MakerSerializer(queryset, many=True).data)()
        return Response(data, status=status.HTTP_200_OK)

    async def post(self, request):
        """The method used to create a maker order"""

        maker = MakerSerializer(data=request.data)
        await sync_to_async(maker.is_valid)(raise_exception=True)
        maker.save(filled=Decimal("0"))

        if maker.instance is not None:
            maker.instance = await maker.instance

        return Response(maker.data, status=status.HTTP_200_OK)


class BotView(APIView):
    """View used to create and retrieve bots"""

    def get_authenticators(self):
        data = super().get_authenticators()
        return data + [auth() for auth in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "authentication_classes", [])]  # type: ignore

    def get_permissions(self):
        data = super().get_permissions()
        return data + [permission() for permission in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "permission_classes", [])]  # type: ignore

    @authentication_classes([ApiAuthentication])
    @permission_classes([IsAuthenticated])
    async def get(self, request):
        """Returns the user bots list,"""
        if request.auth == "awaitable":
            request.user = (await User.objects.aget_or_create(address=request.user))[0]

        bots = Bot.objects.filter(user=request.user).prefetch_related("orders")
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
        return Response(data, status=status.HTTP_200_OK)
