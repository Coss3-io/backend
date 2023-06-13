from decimal import Decimal
from time import time
from django.urls import reverse
from rest_framework import status
from api.models import User
from api.models.types import Address
from rest_framework.test import APITestCase


class MakerOrderTestCase(APITestCase):
    """Test case for creating an retrieving Maker orders"""

    def test_creating_maker_order_works(self):
        """Checks we can create an order"""

        user = User.objects.create_user(
            address=Address("0xf17f52151EbEF6C7334FAD080c5704D77216b732")
        )
        self.client.force_authenticate(user)  # type: ignore

        data = {
            "amount": Decimal("173e16"),
            "expiry": "9999999999999999",
            "price": Decimal("2e20"),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0x796ee451cdc0b004e494e833a53e6c26b136696bce03a8dc63e2d7df73c09c3f03195e4021cad50bac726364258e024f6f6483eae8fd7b3da5b080717aab24b41c",
            "order_hash": "0x73a4fa8382a91dbeadf8dfaca90219db7541a1955937e7c5529ae7e96788a187",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        print(response.content)
