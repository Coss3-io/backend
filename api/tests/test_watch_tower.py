from asgiref.sync import async_to_sync
from unittest.mock import patch
from datetime import datetime
from decimal import Decimal
from web3 import Web3
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from api.models import User
import api.errors as errors
from api.models.orders import Maker, Bot, Taker
from api.models.types import Address


class MakerCommitTestCase(APITestCase):
    """Class used to check the maker order committing"""

    def setUp(self):
        """Create maker orders to match orders againts"""
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

    def test_maker_matching_works(self):
        """Checks the watch tower commiting function works"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        async_to_sync(User.objects.create_user)(
            address=Address("0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef")
        )

        trades = {
            self.data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

        maker = Maker.objects.get(order_hash=self.data["order_hash"])
        taker = Taker.objects.get(block=block)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The matching request should work properly",
        )

        self.assertDictEqual(
            response.json(), {}, "the response on order matching should be empty"
        )

        self.assertEqual(
            maker.filled,
            Decimal(trades[self.data["order_hash"]]["taker_amount"]),
            "The filled amount should be increased by the trade amount",
        )

        self.assertEqual(
            taker.maker.id,
            maker.id,
            "the associated maker order should be the one created previously",
        )

        self.assertEqual(
            taker.taker_amount,
            Decimal(trades[self.data["order_hash"]]["taker_amount"]),
            "the taker_amount of the taker object should match the one sent",
        )

        self.assertEqual(
            taker.fees,
            Decimal(trades[self.data["order_hash"]]["fees"]),
            "the fees of the taker object should match the one sent",
        )

        self.assertEqual(
            taker.is_buyer,
            trades[self.data["order_hash"]]["is_buyer"],
            "the is_buyer of the taker object should match the one sent",
        )

        self.assertEqual(
            taker.is_buyer,
            trades[self.data["order_hash"]]["base_fees"],
            "the base_fees of the taker object should match the one sent",
        )

        self.assertEqual(
            taker.block,
            block,
            "the block of the taker object should match the one sent",
        )

        self.assertEqual(
            taker.user.address,
            taker_address,
            "the user address of the taker object should match the one sent",
        )

    def test_user_creation_on_matching_works(self):
        """Checks a taker trade creation also creates a user if the user
        does not already exist
        """

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        trades = {
            self.data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

        User.objects.get(address=taker_address)

    def test_maker_order_filling_works(self):
        """Checks filling a regular maker order works"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        trades = {
            self.data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("173e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

        maker = Maker.objects.get(order_hash=self.data["order_hash"])

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The maker filling request should work"
        )

        self.assertDictEqual(response.json(), {}, "The response should be empty")

        self.assertEqual(
            maker.filled,
            maker.amount,
            "The amount filled from the maker should be equal to the maker amount",
        )

        self.assertEqual(
            maker.status,
            Maker.FILLED,
            "The maker order status should be changed to filled",
        )

    def test_matching_two_makers_works(self):
        """Checks the maker matching of two orders works"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("273e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("3e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xc053bde5c83879bbef62ae459fb5941eea31d3bbadf950fd43a0d25f842268b011a5868f16fcbc9e15bd4a2c4ff78c1beb554a3c2aaec072e8cdd312733f5c9e1c",
            "order_hash": "0x45da23039e85988dc7a10b1965cdb641f77c268b4a1a7aff7bd20fecc0884937",
            "is_buyer": False,
        }

        async_to_sync(Maker.objects.create)(
            user=self.user,
            amount=data["amount"],
            expiry=datetime.fromtimestamp(data["expiry"]),
            price=data["price"],
            base_token=Web3.to_checksum_address(data["base_token"]),
            quote_token=Web3.to_checksum_address(data["quote_token"]),
            signature=data["signature"],
            order_hash=data["order_hash"],
            is_buyer=data["is_buyer"],
        )

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        trades = {
            self.data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("387e15")),
                "is_buyer": True,
            }
        }

        block2 = 14
        trades2 = {
            data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("173e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

            response2 = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block2,
                    "trades": trades2,
                },
            )

        maker = Maker.objects.get(order_hash=self.data["order_hash"])
        maker2 = Maker.objects.get(order_hash=data["order_hash"])

        taker = Taker.objects.get(block=block)
        taker2 = Taker.objects.get(block=block2)

        self.assertEqual(
            response.status_code, HTTP_200_OK, "the first order matching should work"
        )
        self.assertEqual(
            response2.status_code, HTTP_200_OK, "the second order matching should work"
        )

        self.assertDictEqual(
            response.json(), {}, "the response on order matching should be empty"
        )

        self.assertEqual(
            maker.filled,
            Decimal(trades[self.data["order_hash"]]["taker_amount"]),
            "The filled amount should be increased by the trade amount",
        )

        self.assertEqual(
            taker.maker.id,
            maker.id,
            "the associated maker order should be the one created previously",
        )

        self.assertEqual(
            taker.taker_amount,
            Decimal(trades[self.data["order_hash"]]["taker_amount"]),
            "the taker_amount of the taker object should match the one sent",
        )

        self.assertEqual(
            taker.fees,
            Decimal(trades[self.data["order_hash"]]["fees"]),
            "the fees of the taker object should match the one sent",
        )

        self.assertEqual(
            taker.is_buyer,
            trades[self.data["order_hash"]]["is_buyer"],
            "the is_buyer of the taker object should match the one sent",
        )

        self.assertEqual(
            taker.is_buyer,
            trades[self.data["order_hash"]]["base_fees"],
            "the base_fees of the taker object should match the one sent",
        )

        self.assertEqual(
            taker.block,
            block,
            "the block of the taker object should match the one sent",
        )

        self.assertEqual(
            taker.user.address,
            taker_address,
            "the user address of the taker object should match the one sent",
        )

        self.assertDictEqual(
            response2.json(), {}, "the response2 on order matching should be empty"
        )

        self.assertEqual(
            maker2.filled,
            Decimal(trades2[data["order_hash"]]["taker_amount"]),
            "The filled amount should be increased by the trade amount",
        )

        self.assertEqual(
            taker2.maker.id,
            maker2.id,
            "the associated maker order should be the one created previously",
        )

        self.assertEqual(
            taker2.taker_amount,
            Decimal(trades2[data["order_hash"]]["taker_amount"]),
            "the taker_amount of the taker object should match the one sent",
        )

        self.assertEqual(
            taker2.fees,
            Decimal(trades2[data["order_hash"]]["fees"]),
            "the fees of the taker object should match the one sent",
        )

        self.assertEqual(
            taker2.is_buyer,
            trades2[data["order_hash"]]["is_buyer"],
            "the is_buyer of the taker object should match the one sent",
        )

        self.assertEqual(
            taker2.is_buyer,
            trades2[data["order_hash"]]["base_fees"],
            "the base_fees of the taker object should match the one sent",
        )

        self.assertEqual(
            taker2.block,
            block2,
            "the block of the taker object should match the one sent",
        )

        self.assertEqual(
            taker2.user.address,
            taker_address,
            "the user address of the taker object should match the one sent",
        )

    def test_filling_two_makers_works(self):
        """Checks filling two makers at once works"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("273e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("3e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xc053bde5c83879bbef62ae459fb5941eea31d3bbadf950fd43a0d25f842268b011a5868f16fcbc9e15bd4a2c4ff78c1beb554a3c2aaec072e8cdd312733f5c9e1c",
            "order_hash": "0x45da23039e85988dc7a10b1965cdb641f77c268b4a1a7aff7bd20fecc0884937",
            "is_buyer": False,
        }

        async_to_sync(Maker.objects.create)(
            user=self.user,
            amount=data["amount"],
            expiry=datetime.fromtimestamp(data["expiry"]),
            price=data["price"],
            base_token=Web3.to_checksum_address(data["base_token"]),
            quote_token=Web3.to_checksum_address(data["quote_token"]),
            signature=data["signature"],
            order_hash=data["order_hash"],
            is_buyer=data["is_buyer"],
        )

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        trades = {
            self.data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("173e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("387e15")),
                "is_buyer": True,
            }
        }

        block2 = 14
        trades2 = {
            data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("273e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

            response2 = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block2,
                    "trades": trades2,
                },
            )

        maker = Maker.objects.get(order_hash=self.data["order_hash"])
        maker2 = Maker.objects.get(order_hash=data["order_hash"])

        self.assertDictEqual(
            response.json(), {}, "the order matching response should be empty"
        )
        self.assertEqual(
            maker.filled, maker.amount, "the first maker order should be filled"
        )

        self.assertEqual(
            maker2.filled, maker2.amount, "the second maker order should be filled"
        )

    def test_matching_an_order_without_trades_fails(self):
        """Checks creating a matching without trade field fails"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        trades = {
            self.data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    # "trades": trades,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without trade field should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"trades": [errors.General.MISSING_FIELD.format("trades")]},
            "the request without trade field should fail",
        )

    def test_matching_without_block_fails(self):
        """Checks sending a matching request without block fails"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        trades = {
            self.data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    # "block": block,
                    "trades": trades,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without block field should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"block": [errors.General.MISSING_FIELD.format("block")]},
            "the request without block field should fail",
        )

    def test_matching_without_taker_fails(self):
        """Checks sending a matching request without taker fails"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        trades = {
            self.data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    # "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without taker field should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"taker": [errors.General.MISSING_FIELD.format("taker")]},
            "the request without taker field should fail",
        )

    def test_matching_with_wrong_taker_fails(self):
        """Checks sending a matching request with wrong taker fails"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        trades = "hello"

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with wrong taker field should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"trades": [errors.Order.TRADE_FIELD_FORMAT_ERROR]},
            "the request with wrong taker field should fail",
        )

    def test_matching_with_wrong_checksum_fails(self):
        """Checks sending a matching request with wrong checksum fails"""

        taker_address = "0xc5fdf4076b8F3a5357c5E395ab970B5B54098Fef"
        block = 12

        trades = {
            self.data["order_hash"]: {
                "taker_amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without taker checksum should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Address.WRONG_CHECKSUM]},
            "the request with wrong taker checksum should fail",
        )

    def test_matching_with_wrong_hashed_fails(self):
        """Checks sending a matching request with trades not fitting the format fails"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        trades = {
            "0x1": {"test": 1},
            "0x2": {"test": 2},
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the request with wrong orders hashes should fail",
        )

        self.assertEqual(response.json(), {"error": [errors.Order.TRADE_DATA_ERROR]})

    def test_matching_without_maker_found_fails(self):
        """Checks trying to match without makers found fails"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        trades = {
            "0x42da23039e85988dc7a10b1965cdb641f77c268b4a1a7aff7bd20fecc0884937": {
                "test": 1
            },
            "0x46da23039e85988dc7a10b1965cdb641f77c268b4a1a7aff7bd20fecc0884937": {
                "test": 2
            },
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the request without makers found should fail",
        )

        self.assertEqual(response.json(), {"error": [errors.Order.NO_MAKER_FOUND]})


class MakerCancellationTestCase(APITestCase):
    """Class used to check the maker cancellation behaviour"""

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

    def test_maker_cancellation_works(self):
        """Checks maker order cancellation works"""

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.delete(
                reverse("api:wt"),
                format="json",
                data={
                    "order_hash": self.data.get("order_hash"),
                },
            )

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The cancellation request should work"
        )

        self.assertDictEqual(
            response.json(), {}, "the response should be empty on order cancellation"
        )

    def test_maker_cancellation_no_maker_fails(self):
        """Checks maker order cancellation without maker found fails"""

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.delete(
                reverse("api:wt"),
                format="json",
                data={
                    "order_hash": "0x43eba4e68fb71ce7c24129b2c31165df0a59f0802c90fa44040e7858e94c12e5",
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The cancellation request should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"order_hash": [errors.Order.NO_MAKER_FOUND]},
            "with no maker order found the request should fail",
        )

    def test_maker_cancellation_twice_fails(self):
        """Checks maker order cancellation twice fails"""

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            self.client.delete(
                reverse("api:wt"),
                format="json",
                data={
                    "order_hash": self.data.get("order_hash"),
                },
            )
            response = self.client.delete(
                reverse("api:wt"),
                format="json",
                data={
                    "order_hash": self.data.get("order_hash"),
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The second cancellation request should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Order.MAKER_ALREADY_CANCELLED]},
            "The error should say that maker is already cancelled",
        )


class MakerBotCommitTestCase(APITestCase):
    """Class used to check the behaviour of bot replacement orders"""

    def setUp(self):
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xf17f52151EbEF6C7334FAD080c5704D77216b732")
        )

        self.data = {
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

        self.client.post(reverse("api:bot"), data=self.data)

    def test_maker_replacement_buy_commit(self):
        """Checks committing a replacement maker buy order works"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12
        taker_amount = "{0:f}".format(Decimal("73e16"))
        fees = "{0:f}".format(Decimal("365e15"))
        maker = Maker.objects.get(price=Decimal("11e17"))
        trades = {
            maker.order_hash: {
                "taker_amount": taker_amount,
                "base_fees": True,
                "fees": fees,
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )
        maker.refresh_from_db()
        taker = Taker.objects.get(user__address=taker_address)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The bot replacement committing should work",
        )
        self.assertEqual(response.json(), {}, "On sucess the response should be empty")

        self.assertEqual(
            maker.filled,
            Decimal(taker_amount),
            "The amount filled should be reported into the maker order",
        )

        self.assertEqual(
            taker.taker_amount,
            Decimal(taker_amount),
            "The taker amount should be reported into the taker object",
        )
        self.assertEqual(
            taker.maker, maker, "The maker of the taker should be the matched maker"
        )
        self.assertEqual(taker.block, block, "The taker block should be block sent")
        self.assertEqual(
            taker.base_fees,
            trades[maker.order_hash]["base_fees"],
            "The base fees field should be reported into the created taker object",
        )

        self.assertEqual(
            taker.is_buyer,
            trades[maker.order_hash]["is_buyer"],
            "The is_buyer field should be reported into the created taker object",
        )

        self.assertEqual(
            taker.base_fees,
            Decimal(trades[maker.order_hash]["base_fees"]),
            "The base_fees field should be reported into the taker object",
        )

    def test_maker_replacement_buy_commit_already_trade_order(self):
        """Checks committing a replacement maker buy order works
        even if the order is filled a bit"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12
        taker_amount = "{0:f}".format(Decimal("73e16"))
        fees = "{0:f}".format(Decimal("365e15"))
        maker = Maker.objects.get(price=Decimal("11e17"))
        maker.filled = taker_amount
        maker.save(update_fields=["filled"])

        trades = {
            maker.order_hash: {
                "taker_amount": taker_amount,
                "base_fees": True,
                "fees": fees,
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )
        maker.refresh_from_db()
        taker = Taker.objects.get(user__address=taker_address)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The bot replacement committing should work",
        )
        self.assertEqual(response.json(), {}, "On sucess the response should be empty")

        self.assertEqual(
            maker.filled,
            Decimal(taker_amount) * 2,
            "The amount filled should be twice the first filled amount",
        )

        self.assertEqual(
            taker.taker_amount,
            Decimal(taker_amount),
            "The taker amount should be reported into the taker object",
        )
        self.assertEqual(
            taker.maker, maker, "The maker of the taker should be the matched maker"
        )
        self.assertEqual(taker.block, block, "The taker block should be block sent")
        self.assertEqual(
            taker.base_fees,
            trades[maker.order_hash]["base_fees"],
            "The base fees field should be reported into the created taker object",
        )

        self.assertEqual(
            taker.is_buyer,
            trades[maker.order_hash]["is_buyer"],
            "The is_buyer field should be reported into the created taker object",
        )

        self.assertEqual(
            taker.base_fees,
            Decimal(trades[maker.order_hash]["base_fees"]),
            "The base_fees field should be reported into the taker object",
        )

    def test_mulitple_taker_commit(self):
        """Checks that multiple commit works"""
        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        maker = Maker.objects.get(price=Decimal("11e17"))
        maker2 = Maker.objects.get(price=Decimal("12e17"))

        trades = {
            maker.order_hash: {
                "taker_amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            },
            maker2.order_hash: {
                "taker_amount": "{0:f}".format(Decimal("75e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("360e15")),
                "is_buyer": True,
            },
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

        maker.refresh_from_db()
        maker2.refresh_from_db()

        taker = Taker.objects.get(user__address=taker_address, maker=maker)
        taker2 = Taker.objects.get(user__address=taker_address, maker=maker2)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The response on multiple taker commit should work",
        )
        self.assertEqual(response.json(), {}, "The response should be empty on success")

        self.assertEqual(
            maker.filled,
            Decimal(trades[maker.order_hash]["taker_amount"]),
            "The maker amoout should be uptades after the trades",
        )

        self.assertEqual(
            maker2.filled,
            Decimal(trades[maker2.order_hash]["taker_amount"]),
            "The maker amoout should be uptades after the trades",
        )

        self.assertEqual(
            taker.taker_amount,
            Decimal(trades[maker.order_hash]["taker_amount"]),
            "The taker amount should be reported into the taker object",
        )
        self.assertEqual(
            taker.maker, maker, "The maker of the taker should be the matched maker"
        )
        self.assertEqual(taker.block, block, "The taker block should be block sent")
        self.assertEqual(
            taker.base_fees,
            trades[maker.order_hash]["base_fees"],
            "The base fees field should be reported into the created taker object",
        )

        self.assertEqual(
            taker.is_buyer,
            trades[maker.order_hash]["is_buyer"],
            "The is_buyer field should be reported into the created taker object",
        )

        self.assertEqual(
            taker.base_fees,
            Decimal(trades[maker.order_hash]["base_fees"]),
            "The base_fees field should be reported into the taker object",
        )

        self.assertEqual(
            taker2.taker_amount,
            Decimal(trades[maker2.order_hash]["taker_amount"]),
            "The taker amount should be reported into the taker object",
        )
        self.assertEqual(
            taker2.maker, maker2, "The maker of the taker should be the matched maker"
        )
        self.assertEqual(taker2.block, block, "The taker block should be block sent")
        self.assertEqual(
            taker2.base_fees,
            trades[maker2.order_hash]["base_fees"],
            "The base fees field should be reported into the created taker object",
        )

        self.assertEqual(
            taker2.is_buyer,
            trades[maker2.order_hash]["is_buyer"],
            "The is_buyer field should be reported into the created taker object",
        )

        self.assertEqual(
            taker2.base_fees,
            Decimal(trades[maker2.order_hash]["base_fees"]),
            "The base_fees field should be reported into the taker object",
        )

    def test_maker_replacement_seller_commit(self):
        """Checks seller commiting works"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        maker = Maker.objects.get(price=Decimal("9e17"))
        trades = {
            maker.order_hash: {
                "taker_amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": False,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )
        maker.refresh_from_db()
        taker = Taker.objects.get(user__address=taker_address)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The bot replacement committing should work",
        )
        self.assertEqual(response.json(), {}, "On sucess the response should be empty")

        self.assertEqual(
            maker.filled,
            Decimal(trades[maker.order_hash]["taker_amount"]),
            "The amount filled should be reported into the maker order",
        )

        self.assertEqual(
            taker.taker_amount,
            Decimal(trades[maker.order_hash]["taker_amount"]),
            "The taker amount should be reported into the taker object",
        )
        self.assertEqual(
            taker.maker, maker, "The maker of the taker should be the matched maker"
        )
        self.assertEqual(taker.block, block, "The taker block should be block sent")
        self.assertEqual(
            taker.base_fees,
            trades[maker.order_hash]["base_fees"],
            "The base fees field should be reported into the created taker object",
        )

        self.assertEqual(
            taker.is_buyer,
            trades[maker.order_hash]["is_buyer"],
            "The is_buyer field should be reported into the created taker object",
        )

        self.assertEqual(
            taker.base_fees,
            Decimal(trades[maker.order_hash]["base_fees"]),
            "The base_fees field should be reported into the taker object",
        )

    def test_maker_seller_commit_same_side_no_previous_trades_fails(self):
        """Checks seller commiting works"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12

        maker = Maker.objects.get(price=Decimal("9e17"))
        trades = {
            maker.order_hash: {
                "taker_amount": "{0:f}".format(Decimal("73e16")),
                "base_fees": True,
                "fees": "{0:f}".format(Decimal("365e15")),
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request should fail if no trades were made",
        )

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Order.ORDER_POSITIVE_VIOLATION]},
            "with no previous trades an order violation should be raised",
        )


class MakerBotFeesTestCase(APITestCase):
    """Checks the maker fees for replacement orders are handled well"""

    def setUp(self):
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xf17f52151EbEF6C7334FAD080c5704D77216b732")
        )

        self.data = {
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

        self.client.post(reverse("api:bot"), data=self.data)

    def test_sell_maker_opp_side_lt_2000(self):
        """Checks the fees on a particular scenario are handled well"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12
        taker_amount = "{0:f}".format(Decimal("73e16"))
        fees = "{0:f}".format(Decimal("365e15"))
        maker = Maker.objects.get(price=Decimal("11e17"))
        trades = {
            maker.order_hash: {
                "taker_amount": taker_amount,
                "base_fees": True,
                "fees": fees,
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )
        maker.refresh_from_db()

        fees = (
            (
                maker.price * (maker.bot.maker_fees + Decimal("1000")) / Decimal("1000")
                - maker.price
            )
            * Decimal(taker_amount)
            / Decimal("1e18")
        ).quantize(Decimal("1."))

        self.assertEqual(response.status_code, HTTP_200_OK, "The request should work")
        self.assertEqual(response.json(), {}, "On success the response should be empty")
        self.assertEqual(
            maker.bot.fees_earned,
            fees,
            "The negative fees generated should be updated to the bot ",
        )

    def test_sell_maker_opp_side_gt_2000(self):
        """Checks the fees on a particular scenario are handled well"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12
        taker_amount = "{0:f}".format(Decimal("73e16"))
        fees = "{0:f}".format(Decimal("365e15"))

        maker = Maker.objects.get(price=Decimal("11e17"))
        maker.bot.maker_fees = Decimal("5e14")
        maker.bot.save(update_fields=["maker_fees"])

        trades = {
            maker.order_hash: {
                "taker_amount": taker_amount,
                "base_fees": True,
                "fees": fees,
                "is_buyer": True,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )
        maker.refresh_from_db()

        fees = (
            maker.bot.maker_fees * Decimal(taker_amount) / Decimal("1e18")
        ).quantize(Decimal("1."))

        self.assertEqual(response.status_code, HTTP_200_OK, "The request should work")
        self.assertEqual(response.json(), {}, "On success the response should be empty")
        self.assertEqual(
            maker.bot.fees_earned,
            fees,
            "The negative fees generated should be updated to the bot ",
        )

    def test_sell_maker_same_side_lt_2000(self):
        """Checks the fees on a particular scenario are handled well"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12
        taker_amount = "{0:f}".format(Decimal("73e16"))
        fees = "{0:f}".format(Decimal("365e15"))

        maker = Maker.objects.get(price=Decimal("11e17"))
        maker.filled = Decimal(taker_amount)
        maker.save(update_fields=["filled"])

        trades = {
            maker.order_hash: {
                "taker_amount": taker_amount,
                "base_fees": True,
                "fees": fees,
                "is_buyer": False,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )
        maker.refresh_from_db()

        fees = (
            (
                maker.price
                - maker.price
                * Decimal("1000")
                / (maker.bot.maker_fees + Decimal("1000"))
            )
            * Decimal(taker_amount)
            / Decimal("1e18")
        ).quantize(Decimal("1."))

        self.assertEqual(response.status_code, HTTP_200_OK, "The request should work")
        self.assertEqual(response.json(), {}, "On success the response should be empty")
        self.assertEqual(
            maker.bot.fees_earned,
            fees,
            "The negative fees generated should be updated to the bot ",
        )

    def test_sell_maker_same_side_gt_2000(self):
        """Checks the fees on a particular scenario are handled well"""

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12
        taker_amount = "{0:f}".format(Decimal("73e16"))
        fees = "{0:f}".format(Decimal("365e15"))

        maker = Maker.objects.get(price=Decimal("11e17"))
        maker.filled = Decimal(taker_amount)
        maker.bot.maker_fees = Decimal("5e14")
        maker.bot.save(update_fields=["maker_fees"])
        maker.save(update_fields=["filled"])

        trades = {
            maker.order_hash: {
                "taker_amount": taker_amount,
                "base_fees": True,
                "fees": fees,
                "is_buyer": False,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )
        maker.refresh_from_db()

        fees = (
            maker.bot.maker_fees * Decimal(taker_amount) / Decimal("1e18")
        ).quantize(Decimal("1."))

        self.assertEqual(response.status_code, HTTP_200_OK, "The request should work")
        self.assertEqual(response.json(), {}, "On success the response should be empty")
        self.assertEqual(
            maker.bot.fees_earned,
            fees,
            "The negative fees generated should be updated to the bot ",
        )

    def test_buy_maker_opp_side_lt_2000(self):
        """Checks the fees on a particular scenario are handled well"""
        from django.db import connection

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12
        taker_amount = "{0:f}".format(Decimal("73e16"))
        fees = "{0:f}".format(Decimal("365e15"))
        maker = Maker.objects.get(price=Decimal("9e17"))
        trades = {
            maker.order_hash: {
                "taker_amount": taker_amount,
                "base_fees": True,
                "fees": fees,
                "is_buyer": False,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )
        maker.refresh_from_db()
        fees = (
            (
                maker.price
                - maker.price
                * Decimal("1000")
                / (maker.bot.maker_fees + Decimal("1000"))
            )
            * Decimal(taker_amount)
            / Decimal("1e18")
        ).quantize(Decimal("1."))

        self.assertEqual(response.status_code, HTTP_200_OK, "The request should work")
        self.assertEqual(response.json(), {}, "On success the response should be empty")
        self.assertEqual(
            maker.bot.fees_earned,
            fees,
            "The negative fees generated should be updated to the bot ",
        )

    def test_buy_maker_opp_side_gt_2000(self):
        """Checks the fees on a particular scenario are handled well"""
        from django.db import connection

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12
        taker_amount = "{0:f}".format(Decimal("73e16"))
        fees = "{0:f}".format(Decimal("365e15"))

        maker = Maker.objects.get(price=Decimal("9e17"))
        maker.bot.maker_fees = Decimal("77e14")
        maker.bot.save(update_fields=["maker_fees"])

        trades = {
            maker.order_hash: {
                "taker_amount": taker_amount,
                "base_fees": True,
                "fees": fees,
                "is_buyer": False,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )
        maker.refresh_from_db()
        fees = (
            maker.bot.maker_fees * Decimal(taker_amount) / Decimal("1e18")
        ).quantize(Decimal("1."))

        self.assertEqual(response.status_code, HTTP_200_OK, "The request should work")
        self.assertEqual(response.json(), {}, "On success the response should be empty")
        self.assertEqual(
            maker.bot.fees_earned,
            fees,
            "The negative fees generated should be updated to the bot ",
        )

    def test_buy_maker_same_side_lt_2000(self):
        """Checks the fees on a particular scenario are handled well"""
        from django.db import connection

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12
        taker_amount = "{0:f}".format(Decimal("73e16"))
        fees = "{0:f}".format(Decimal("365e15"))

        maker = Maker.objects.get(price=Decimal("9e17"))
        maker.filled = Decimal(taker_amount)
        maker.save(update_fields=["filled"])

        trades = {
            maker.order_hash: {
                "taker_amount": taker_amount,
                "base_fees": True,
                "fees": fees,
                "is_buyer": False,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )
        maker.refresh_from_db()
        fees = (
            (
                maker.price
                - maker.price
                * Decimal("1000")
                / (maker.bot.maker_fees + Decimal("1000"))
            )
            * Decimal(taker_amount)
            / Decimal("1e18")
        ).quantize(Decimal("1."))

        self.assertEqual(response.status_code, HTTP_200_OK, "The request should work")
        self.assertEqual(response.json(), {}, "On success the response should be empty")
        self.assertEqual(
            maker.bot.fees_earned,
            fees,
            "The negative fees generated should be updated to the bot ",
        )

    def test_buy_maker_same_side_gt_2000(self):
        """Checks the fees on a particular scenario are handled well"""
        from django.db import connection

        taker_address = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"
        block = 12
        taker_amount = "{0:f}".format(Decimal("73e16"))
        fees = "{0:f}".format(Decimal("365e15"))

        maker = Maker.objects.get(price=Decimal("9e17"))
        maker.filled = Decimal(taker_amount)
        maker.bot.maker_fees = Decimal("71e14")
        maker.bot.save(update_fields=["maker_fees"])
        maker.save(update_fields=["filled"])

        trades = {
            maker.order_hash: {
                "taker_amount": taker_amount,
                "base_fees": True,
                "fees": fees,
                "is_buyer": False,
            }
        }

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker_address,
                    "block": block,
                    "trades": trades,
                },
            )
        maker.refresh_from_db()
        fees = (
            (maker.bot.maker_fees) * Decimal(taker_amount) / Decimal("1e18")
        ).quantize(Decimal("1."))

        self.assertEqual(response.status_code, HTTP_200_OK, "The request should work")
        self.assertEqual(response.json(), {}, "On success the response should be empty")
        self.assertEqual(
            maker.bot.fees_earned,
            fees,
            "The negative fees generated should be updated to the bot ",
        )
