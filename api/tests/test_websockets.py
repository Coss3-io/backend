from decimal import Decimal
from json import loads
from unittest.mock import patch
from django.urls import reverse
from web3 import Web3
from rest_framework.test import APITestCase
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from channels.testing import WebsocketCommunicator
from backend.asgi import ws_asgi_app
from api.messages import WStypes


class WebsocketFramesTestCase(APITestCase):
    """Class used to verify the frames sent by the websocket"""

    async def test_websocket_frame_order_creation(self):
        """Checks a websocket frame is sent on order creation"""

        communicator = WebsocketCommunicator(ws_asgi_app, "/ws")
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        data = {
            "address": Web3.to_checksum_address(
                "0xF17f52151EbEF6C7334FAD080c5704D77216b732"
            ),
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": Web3.to_checksum_address(
                "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520"
            ),
            "quote_token": Web3.to_checksum_address(
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            ),
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
        }
        response = await self.async_client.post(reverse("api:order"), data=data)  # type: ignore

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The order creation request should work"
        )

        message = await communicator.receive_from()
        self.assertDictEqual(
            loads(message),
            {WStypes.NEW_MAKER: response.json()},
            "The websocket message should contain the maker just created",
        )
