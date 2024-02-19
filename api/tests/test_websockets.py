import hmac
from decimal import Decimal
from asyncio import TimeoutError
from asgiref.sync import async_to_sync
from datetime import datetime
from unittest.mock import patch
from json import loads, dumps
from time import time
from django.urls import reverse
from regex import P
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
            address=Address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
        )

        self.data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
            "is_buyer": False,
            "timestamp": int(time()),
            'base_fees': "0",
            'quote_fees': "0",
        }

        async_to_sync(Maker.objects.create)(
            user=self.user,
            amount=self.data["amount"],
            expiry=datetime.fromtimestamp(self.data["expiry"]),
            price=self.data["price"],
            base_token=Address(self.data["base_token"]),
            quote_token=Address(self.data["quote_token"]),
            signature=self.data["signature"],
            order_hash=self.data["order_hash"],
            chain_id=self.data["chain_id"],
            is_buyer=self.data["is_buyer"],
        )

        self.bot = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
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

        chain_id = 31337
        base_token = Address("0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF")
        quote_token = Address("0x345CA3e014Aaf5dcA488057592ee47305D9B3e10")

        communicator = WebsocketCommunicator(
            ws_asgi_app, f"/ws/trade/{chain_id}/{base_token}/{quote_token}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        data = {
            "address": Address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8"),
            "amount": "{0:f}".format(Decimal("10e18")),
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("1e18")),
            "base_token": base_token,
            "quote_token": quote_token,
            "chain_id": chain_id,
            "signature": "0x20ac5d31e978ea2f5d1dc16b08789d61bd58fcdf0ef6475db340354b1e3dab0c6f48576498037d4455e9c99695c22a02fa203ade35bb8b81e4e123a0e819a0041c",
            "order_hash": "0xa6a16391a147c1af24904cd5d0bfda49786a85e6359ecb34cef2113a2b5550f8",
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

    async def test_websocket_other_pair_not_frame(self):
        """Checks that the websockets of other pair are not received by other pairs"""

        chain_id = 31337
        base_token = Address("0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF")
        quote_token = Address("0x345CA3e014Aaf5dcA488057592ee47305D9B3e10")

        communicator = WebsocketCommunicator(
            ws_asgi_app,
            f"/ws/trade/{chain_id}/{base_token}/0x345CA3e014Aaf5dcA488057592ee47305D9B3e11",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        data = {
            "address": Address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8"),
            "amount": "{0:f}".format(Decimal("10e18")),
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("1e18")),
            "base_token": base_token,
            "quote_token": quote_token,
            "chain_id": chain_id,
            "signature": "0x20ac5d31e978ea2f5d1dc16b08789d61bd58fcdf0ef6475db340354b1e3dab0c6f48576498037d4455e9c99695c22a02fa203ade35bb8b81e4e123a0e819a0041c",
            "order_hash": "0xa6a16391a147c1af24904cd5d0bfda49786a85e6359ecb34cef2113a2b5550f8",
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

        with self.assertRaises(TimeoutError):
            await communicator.receive_from()

    async def test_websocket_frame_bot_creation(self):
        """Checks a websocket frame is sent on bot creation"""

        chain_id = 31337
        base_token = "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF"
        quote_token = "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10"

        async for bot in Bot.objects.all():
            await bot.adelete()  # type: ignore
        communicator = WebsocketCommunicator(
            ws_asgi_app, f"/ws/trade/{chain_id}/{base_token}/{quote_token}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "expiry": 2114380801,
            "chain_id": chain_id,
            "signature": "0xae1dd3d878120fef75d9f21890a1c13bc60a709a94186f32cbaf5feb10ffc076612bae739398e9d4f3fc451f19266207d2609a1885e953ec572c5738525a25fa1b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": base_token,
            "quote_token": quote_token,
        }

        response = await self.async_client.post(reverse("api:bot"), data=data)  # type: ignore

        message = await communicator.receive_from()
        self.assertDictEqual(
            loads(message),
            {WStypes.NEW_BOT: response.json()},
            "The websocket message should contain the bot just created",
        )

    async def test_websocket_frame_stacking_deposit_creation(self):
        """Checks a websocket frame is sent on stacking deposit"""

        chain_id = "31337"
        communicator = WebsocketCommunicator(ws_asgi_app, f"/ws/stacking/{chain_id}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        data = {
            "address": Address("0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef"),
            "amount": "{0:f}".format(Decimal("173e16")),
            "chain_id": chain_id,
            "slot": "23",
            "withdraw": "0",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()
        data["withdraw"] = int(data["withdraw"])

        await self.async_client.post(reverse("api:stacking"), data=data)  # type: ignore
        message = await communicator.receive_from()

        data["slot"] = int(data["slot"])
        data["chain_id"] = int(data["chain_id"])
        del data["timestamp"]
        del data["signature"]

        self.assertDictEqual(
            loads(message),
            {WStypes.NEW_STACKING: data},
            "The websocket message should contain the stacking entry just created",
        )

    async def test_websocket_frame_stacking_withdrawal_creation(self):
        """Checks a websocket frame is sent on stacking withdrawal"""

        chain_id = "31337"
        communicator = WebsocketCommunicator(ws_asgi_app, f"/ws/stacking/{chain_id}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        data = {
            "address": Address("0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef"),
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
            "withdraw": "1",
            "chain_id": chain_id,
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
        data["chain_id"] = int(data["chain_id"])
        data["withdraw"] = True
        data["amount"] = ("-" if data["withdraw"] else "") + data["amount"]
        del data["timestamp"]
        del data["signature"]

        self.assertDictEqual(
            loads(message),
            {WStypes.NEW_STACKING: data},
            "The websocket message should contain the stacking entry just created",
        )

    async def test_websocket_frame_stacking_fees_creation(self):
        """Checks a websocket frame is sent on stacking fees entry creation"""

        chain_id = "31337"
        communicator = WebsocketCommunicator(ws_asgi_app, f"/ws/stacking/{chain_id}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        data = {
            "token": Address("0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef"),
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
            "chain_id": chain_id,
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
        data["chain_id"] = int(data["chain_id"])
        del data["timestamp"]
        del data["signature"]

        self.assertDictEqual(
            loads(message),
            {WStypes.NEW_FEES: data},
            "The websocket message should contain the stacking fees just created",
        )

    async def test_websocket_frame_stacking_fees_withdrawal_creation(self):
        """Checks a websocket frame is sent on stacking fees withdrawal creation"""

        chain_id = "31337"
        communicator = WebsocketCommunicator(ws_asgi_app, f"/ws/stacking/{chain_id}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        data = {
            "token": Address("0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef"),
            "address": "0xC5fdF4176b8F3A5357c5E395ab970B5B54098Fef",
            "slot": "23",
            "chain_id": chain_id,
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        await self.async_client.post(reverse("api:fees-withdrawal"), data=data)  # type: ignore
        message = await communicator.receive_from()

        data["slot"] = int(data["slot"])
        data["chain_id"] = int(data["chain_id"])
        data["address"] = Address(data["address"])
        del data["timestamp"]
        del data["signature"]

        self.assertDictEqual(
            loads(message),
            {WStypes.NEW_FSA_WITHDRAWAL: data},
            "The websocket message should contain the stacking fees withdrawal just created",
        )

    async def test_websocket_frame_maker_deletion(self):
        """Checks the websocket frame is sent well on order deletion"""

        chain_id = 31337
        communicator = WebsocketCommunicator(
            ws_asgi_app,
            f"ws/trade/{chain_id}/{self.data['base_token']}/{self.data['quote_token']}",
        )
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

        taker_address = Address("0xf17f52151EbEF6C7334FAD080c5704D77216b733")
        maker = await Maker.objects.select_related("bot").aget(price=Decimal("5e17"))
        block = 19
        prev_fees = Decimal("100e18")
        chain_id = 31337
        communicator = WebsocketCommunicator(
            ws_asgi_app, f"/ws/trade/{chain_id}/{maker.base_token}/{maker.quote_token}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")
        communicator_2 = WebsocketCommunicator(
            ws_asgi_app,
            f"/ws/trade/{self.data['chain_id']}/{self.data['base_token']}/{self.data['quote_token']}",
        )
        connected, _ = await communicator_2.connect()
        self.assertTrue(connected, "The websocket should be connected on test startup")

        maker.bot.fees_earned = prev_fees
        await maker.bot.asave()

        trades = {
            self.data["order_hash"]: {
                "amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            },
            maker.order_hash: {
                "amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("360e15")),
                "is_buyer": False,
            },
        }

        maker = await Maker.objects.select_related("bot").aget(price=Decimal("5e17"))
        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = await self.async_client.post(  # type: ignore
                reverse("api:wt"),
                content_type="application/json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                    "chain_id": chain_id,
                },
            )
            self.assertEqual(
                response.status_code, HTTP_200_OK, "The request should work"
            )
        await maker.arefresh_from_db(fields=["filled"])

        fees = (
            (
                maker.price
                - maker.price
                * Decimal("1000")
                / (maker.bot.maker_fees + Decimal("1000"))
            )
            * Decimal(trades[maker.order_hash]["amount"])
            / Decimal("1e18")
        ).quantize(Decimal("1."))

        bot_message = await communicator.receive_from()
        message = await communicator_2.receive_from()

        self.data["filled"] = "{0:f}".format(Decimal("73e16"))
        

        self.data["bot"] = None
        self.data["status"] = "OPEN"
        data = {
            WStypes.MAKERS_UPDATE: [self.data],
            WStypes.NEW_TAKERS: [
                {
                    "block": block,
                    "amount": trades[self.data["order_hash"]]["amount"],
                    "fees": trades[self.data["order_hash"]]["fees"],
                    "is_buyer": trades[self.data["order_hash"]]["is_buyer"],
                    "base_fees": trades[self.data["order_hash"]]["base_fees"],
                    "address": taker_address,
                    "chain_id": chain_id,
                    "maker_hash": self.data["order_hash"],
                },
            ],
        }
        bot_data = {
            WStypes.MAKERS_UPDATE: [
                {
                    "address": self.user.address,
                    "amount": "{0:f}".format(Decimal("2e18")),
                    "expiry": 2114380800,
                    "price": "{0:f}".format(maker.price),
                    "base_token": maker.base_token,
                    "quote_token": maker.quote_token,
                    "chain_id": chain_id,
                    "signature": maker.signature,
                    "order_hash": maker.order_hash,
                    "is_buyer": maker.is_buyer,
                    "filled": "{0:f}".format(maker.filled),
                    "timestamp": int(maker.bot.timestamp.timestamp()),
                    "status": maker.get_status_display(),
                    "base_fees": "0",
                    "quote_fees": "0",
                    "bot": {
                        "address": self.user.address,
                        "step": "{0:f}".format(maker.bot.step),
                        "price": "{0:f}".format(maker.bot.price),
                        "maker_fees": "{0:f}".format(maker.bot.maker_fees),
                        "upper_bound": "{0:f}".format(maker.bot.upper_bound),
                        "lower_bound": "{0:f}".format(maker.bot.lower_bound),
                        "chain_id": chain_id,
                        "fees_earned": "{0:f}".format(
                            Decimal(fees) + Decimal(maker.bot.fees_earned)
                        ),
                        "timestamp": int(maker.bot.timestamp.timestamp()),
                    },
                },
            ],
            WStypes.NEW_TAKERS: [
                {
                    "block": block,
                    "amount": trades[maker.order_hash]["amount"],
                    "fees": trades[maker.order_hash]["fees"],
                    "is_buyer": trades[maker.order_hash]["is_buyer"],
                    "base_fees": trades[maker.order_hash]["base_fees"],
                    "address": taker_address,
                    "chain_id": chain_id,
                    "maker_hash": maker.order_hash,
                },
            ],
        }

        message = loads(message)
        bot_message = loads(bot_message)
        self.assertDictEqual(
            data,
            message,
            "The websocket of the regular order should contain all the infos needed",
        )
        self.maxDiff = None
        self.assertDictEqual(
            bot_data,
            bot_message,
            "The websocket of the bot order should contain all the infos needed",
        )
