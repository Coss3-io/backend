from asgiref.sync import async_to_sync
from unittest.mock import patch
from datetime import datetime
from decimal import Decimal
from web3 import Web3
from django.urls import reverse
from rest_framework.test import APITestCase
from api.models import User
from api.models.orders import Maker, Bot
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

        taker = "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef"

        with patch("api.views.watch_tower.WatchTowerView.permission_classes", []):
            response = self.client.post(
                reverse("api:wt"),
                format="json",
                data={
                    "taker": taker,
                    "block": 12,
                    "trades": {
                        "orderhash": {
                            "taker_amount": 0,
                            "base_fees": True,
                            "fees": 0,
                            "is_buyer": True,
                        }
                    },
                },
            )
