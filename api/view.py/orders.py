from decimal import Decimal, InvalidOperation
from adrf.views import APIView
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from api.models.orders import Maker, Taker
from api.models.types import Address, Signature, KeccakHash
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

    authentication_classes = [SessionAuthentication]
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

        try:
            if amount := Decimal(request.data.get("amount", 0)) == Decimal("0"):
                return Response(
                    {"detail": "amount field is missing"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except InvalidOperation:
            return Response(
                {"detail": "amount field is not a valid number"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            if price := Decimal(request.data.get("price", 0)) == Decimal("0"):
                return Response(
                    {"detail": "price field is missing"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except InvalidOperation:
            return Response(
                {"detail": "price field is not a valid number"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            if expiry := Decimal(request.data.get("expiry", 0)) == Decimal("0"):
                return Response(
                    {"detail": "expiry field is missing"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except InvalidOperation:
            return Response(
                {"detail": "expiry field is not a valid number"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if base_token := Address(request.data.get("base_token", "0")) == Address("0"):
            return Response(
                {"detail": "base_token field is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quote_token := Address(request.data.get("quote_token", "0")) == Address("0"):
            return Response(
                {"detail": "quote_token field is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order_hash := KeccakHash(request.data.get("order_hash", "0")) == KeccakHash(
            "0"
        ):
            return Response(
                "order_hash field is missing", status=status.HTTP_400_BAD_REQUEST
            )

        if signature := Signature(request.data.get("quote_token", "0")) == KeccakHash(
            "0"
        ):
            return Response(
                {"detail": "quote_token field is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if is_buyer := request.data.get("is_buyer", None) == None:
            return Response(
                {"detail": "is_buyer field is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        maker = MakerSerializer(
            Maker(
                user=request.user,
                expiry=expiry,
                price=price,
                base_token=base_token,
                quote_toke=quote_token,
                signature=signature,
                order_hash=order_hash,
                is_buyer=is_buyer,
            )
        )

        maker.is_valid(raise_exception=True)
        maker.save(filled=Decimal("0"), status=Maker.OPEN)

        return Response(maker.validated_data, status=status.HTTP_200_OK)
