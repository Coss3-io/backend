from decimal import Decimal
from datetime import datetime
from asgiref.sync import sync_to_async
from adrf.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from api.models.orders import Maker
from api.models.types import Address
from api.serializers.orders import MakerSerializer


class OrderView(APIView):
    """View used to retrieve the orders to populate the order books"""

    async def get(self, request: Request):
        """Function used to get all the orders for a given pair"""

        base_token: Address = Address(
            request.query_params.get("base_token", Address("0"))
        )
        quote_token: Address = Address(
            request.query_params.get("quote_token", Address("0"))
        )

        if base_token == Address("0") or quote_token == Address("0"):
            return Response(
                {"detail": "base_token and quote_token params are needed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Maker.objects.filter(base_token=base_token, quote_token=quote_token)

        return Response(
            MakerSerializer(queryset, many=True).data, status=status.HTTP_200_OK
        )


class MakerView(APIView):
    """The views user to retrieve and create Maker Orders"""

    permission_classes = [IsAuthenticated]

    async def get(self, request: Request):
        """The view to retrieve the orders of a user"""

        if request.query_params.get("all", None):
            queryset = Maker.objects.filter(user=request.user)
        else:
            base_token: Address = Address(
                request.query_params.get("base_token", Address("0"))
            )
            quote_token: Address = Address(
                request.query_params.get("quote_token", Address("0"))
            )

            if base_token == Address("0") or quote_token == Address("0"):
                return Response(
                    {"detail": "base_token and quote_token params are needed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            queryset = Maker.objects.filter(
                user=request.user, base_token=base_token, quote_token=quote_token
            )

        return Response(
            MakerSerializer(queryset, many=True).data, status=status.HTTP_200_OK
        )

    async def post(self, request):
        """The method used to create a maker order"""

        data = request.data.copy()
        data.update({"expiry": datetime.fromtimestamp(int(data.get("expiry", 0)))})

        maker = MakerSerializer(data=data, context={"user": request.user})
        await sync_to_async(maker.is_valid)(raise_exception=True)
        await maker.save(filled=Decimal("0"), user=request.user)

        return Response(maker.validated_data, status=status.HTTP_200_OK)
