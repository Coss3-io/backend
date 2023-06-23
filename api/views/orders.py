from decimal import Decimal
from datetime import datetime
from asgiref.sync import sync_to_async
from adrf.views import APIView
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from api.models import User
from api.models.orders import Maker
from api.models.types import Address
from api.serializers.orders import MakerSerializer


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
        ).select_related("user")
        data = await sync_to_async(lambda: MakerSerializer(queryset, many=True).data)()
        return Response(data, status=status.HTTP_200_OK)


class MakerView(APIView):
    """The views user to retrieve and create Maker Orders"""

    def get_permissions(self):
        data = super().get_permissions()
        return data + [permission() for permission in getattr(getattr(self, self.request.method.lower(), self.http_method_not_allowed), "permission_classes", [])]  # type: ignore

    @permission_classes([IsAuthenticated])
    async def get(self, request: Request):
        """The view to retrieve the orders of a user"""
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

        user = (await User.objects.aget_or_create(address=request.data.get("address")))[
            0
        ]
        maker.save(filled=Decimal("0"), user=user)

        if maker.instance is not None:
            maker.instance = await maker.instance

        return Response(maker.data, status=status.HTTP_200_OK)
