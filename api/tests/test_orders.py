from decimal import Decimal
from datetime import datetime
from asgiref.sync import async_to_sync
from django.urls import reverse
from rest_framework import status
from api.models import User
from api.models.orders import Maker
from api.models.types import Address
from rest_framework.test import APITestCase


class MakerOrderTestCase(APITestCase):
    """Test case for creating an retrieving Maker orders"""

    def setUp(self) -> None:
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xf17f52151EbEF6C7334FAD080c5704D77216b732")
        )

    def test_creating_maker_order_works(self):
        """Checks we can create an order"""

        self.client.force_authenticate(user=self.user)  # type: ignore

        data = {
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": "1696667304",
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            "order_hash": "0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)
        self.client.logout()

    def test_retrieve_maker_orders_anon(self):
        """checks we ca retrieve the maker orders being anon"""

        async_to_sync(Maker.objects.create)(
            user=self.user,
            amount="{0:f}".format(Decimal("173e16")),
            expiry=datetime.fromtimestamp(1696667304),
            price="{0:f}".format(Decimal("2e20")),
            base_token="0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            quote_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            signature="0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            order_hash="0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            is_buyer=False,
        )

        data = {
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        }
        response = self.client.get(reverse("api:orders"), data=data)

    def test_sending_id_field_is_not_taken_in_account(self):
        """Checks that a user sending an id along order's field is
        not taken in account for order creation
        """
        pass
