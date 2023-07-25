import hmac
from decimal import Decimal
from asgiref.sync import async_to_sync
from datetime import datetime
from unittest.mock import patch
from json import loads, dumps
from time import time
from django.urls import reverse
from web3 import Web3
from rest_framework.test import APITestCase
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from channels.testing import WebsocketCommunicator
from django.conf import settings
from backend.asgi import ws_asgi_app
from api.messages import WStypes
from api.models import User
from api.models.orders import Maker, Bot
from api.models.types import Address


class WebsocketFramesTestCase(APITestCase):
    """Class used to verify the frames sent by the websocket"""

    def setUp(self):
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xf17f52151EbEF6C7334FAD080c5704D77216b732")
        )

        self.data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xe4609ca8bec52beb499af0ac6e1934798c786b53e6f545f5af28f6117bb675a4500ebbfaa427533d8902e163767d14874ec1d67fcba8c42045ba96f482efc47d1b",
            "order_hash": "0x44eba4e68fb71ce7c24129b2c31165df0a59f0802c90fa44040e7858e94c12e5",
            "is_buyer": False,
        }

        async_to_sync(Maker.objects.create)(
            user=self.user,
            amount=self.data["amount"],
            expiry=datetime.fromtimestamp(self.data["expiry"]),
            price=self.data["price"],
            base_token=Web3.to_checksum_address(self.data["base_token"]),
            quote_token=Web3.to_checksum_address(self.data["quote_token"]),
            signature=self.data["signature"],
            order_hash=self.data["order_hash"],
            is_buyer=self.data["is_buyer"],
        )

        self.bot = {
            "address": "0xF17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        self.client.post(reverse("api:bot"), data=self.bot)

    async def test_websocket_frame_order_creation(self):
        """Checks a websocket frame is sent on order creation"""

        communicator = WebsocketCommunicator(ws_asgi_app, "/ws")
        connected, _ = await communicator.connect()
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

    async def test_websocket_frame_bot_creation(self):
        """Checks a websocket frame is sent on bot creation"""

        async for bot in Bot.objects.all():
            await bot.adelete()
        communicator = WebsocketCommunicator(ws_asgi_app, "/ws")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        data = {
            "address": "0xF17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = await self.async_client.post(reverse("api:bot"), data=data)  # type: ignore

        message = await communicator.receive_from()
        self.assertDictEqual(
            loads(message),
            {WStypes.NEW_BOT: response.json()},
            "The websocket message should contain the bot just created",
        )

    async def test_websocket_frame_stacking_creation(self):
        """Checks a websocket frame is sent on stacking entry creation"""

        communicator = WebsocketCommunicator(ws_asgi_app, "/ws")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        data = {
            "address": Web3.to_checksum_address(
                "0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef"
            ),
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        await self.async_client.post(reverse("api:stacking"), data=data)  # type: ignore
        message = await communicator.receive_from()

        data["slot"] = int(data["slot"])
        del data["timestamp"]
        del data["signature"]

        self.assertDictEqual(
            loads(message),
            {WStypes.NEW_STACKING: data},
            "The websocket message should contain the stacking entry just created",
        )

    async def test_websocket_frame_stacking_fees_creation(self):
        """Checks a websocket frame is sent on stacking fees entry creation"""

        communicator = WebsocketCommunicator(ws_asgi_app, "/ws")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        data = {
            "token": Web3.to_checksum_address(
                "0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef"
            ),
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        await self.async_client.post(reverse("api:stacking-fees"), data=data)  # type: ignore
        message = await communicator.receive_from()

        data["slot"] = int(data["slot"])
        del data["timestamp"]
        del data["signature"]

        self.assertDictEqual(
            loads(message),
            {WStypes.NEW_FEES: data},
            "The websocket message should contain the stacking fees just created",
        )

    async def test_websocket_frame_maker_deletion(self):
        """Checks the websocket frame is sent well on order deletion"""

        communicator = WebsocketCommunicator(ws_asgi_app, "/ws")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            await self.async_client.delete(  # type: ignore
                reverse("api:wt"),
                content_type="application/json",
                format="json",
                data={
                    "order_hash": self.data.get("order_hash"),
                },
            )
        message = await communicator.receive_from()
        self.assertDictEqual(
            loads(message),
            {WStypes.DEL_MAKER: self.data.get("order_hash")},
            "The websocket message should contain the deleted order hash",
        )

    async def test_websocket_frame_maker_update(self):
        """Checks the websocket frame is sent well on order update"""

        taker_address = Web3.to_checksum_address(
            "0xf17f52151EbEF6C7334FAD080c5704D77216b733"
        )
        communicator = WebsocketCommunicator(ws_asgi_app, "/ws")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")
        maker = await Maker.objects.select_related("bot").aget(price=Decimal("5e17"))

        trades = {
            self.data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            },
            maker.order_hash: {
                "taker_amount": "{0:f}".format(Decimal("75e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("360e15")),
                "is_buyer": False,
            },
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            await self.async_client.post(  # type: ignore
                reverse("api:wt"),
                content_type="application/json",
                data={
                    "taker": taker_address,
                    "block": 19,
                    "trades": trades,
                },
            )
        message = await communicator.receive_from()
        self.data["filled"] = "{0:f}".format(Decimal("73e16"))
        maker = await Maker.objects.select_related("bot").aget(price=Decimal("5e17"))

        self.data["bot"] = None
        self.data["status"] = "OPEN"
        data = {
            WStypes.MAKERS_UPDATE: [
                self.data,
                {
                    "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
                    "amount": "{0:f}".format(Decimal("2e18")),
                    "expiry": 2114380800,
                    "price": "{0:f}".format(maker.price),
                    "base_token": maker.base_token,
                    "quote_token": maker.quote_token,
                    "signature": maker.signature,
                    "order_hash": maker.order_hash,
                    "is_buyer": maker.is_buyer,
                    "filled": "{0:f}".format(maker.filled),
                    "status": maker.get_status_display(),
                    "bot": {
                        "step": "{0:f}".format(maker.bot.step),
                        "price": "{0:f}".format(maker.bot.price),
                        "maker_fees": "{0:f}".format(maker.bot.maker_fees),
                        "upper_bound": "{0:f}".format(maker.bot.upper_bound),
                        "lower_bound": "{0:f}".format(maker.bot.lower_bound),
                        "fees_earned": "{0:f}".format(maker.bot.fees_earned),
                    },
                },
            ]
        }

        message = loads(message)
        if (
            data[WStypes.MAKERS_UPDATE][0]["order_hash"]
            == message[WStypes.MAKERS_UPDATE][0]["order_hash"]
        ):
            ws_1, maker_1 = (
                data[WStypes.MAKERS_UPDATE][0],
                message[WStypes.MAKERS_UPDATE][0],
            )
            ws_2, maker_2 = (
                data[WStypes.MAKERS_UPDATE][1],
                message[WStypes.MAKERS_UPDATE][1],
            )
        else:
            ws_1, maker_1 = (
                data[WStypes.MAKERS_UPDATE][0],
                message[WStypes.MAKERS_UPDATE][1],
            )
            ws_2, maker_2 = (
                data[WStypes.MAKERS_UPDATE][1],
                message[WStypes.MAKERS_UPDATE][0],
            )

        self.assertDictEqual(
            ws_1,
            maker_1,
            "The websocket message should contain the first maker update data",
        )
        self.assertDictEqual(
            ws_2,
            maker_2,
            "The websocket message should contain the second maker update data",
        )
