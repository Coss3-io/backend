from decimal import Decimal
from datetime import datetime
from asgiref.sync import async_to_sync
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from api.models import User
from api.errors import ID_SUBMITTED_ERROR
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

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 1696667304,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            "order_hash": "0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            data, response.json(), "The returned order should match the order sent"
        )
        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should work properly"
        )

    def test_retrieve_maker_orders_anon(self):
        """checks we ca retrieve the maker orders being anon"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": datetime.fromtimestamp(1696667304),
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            "order_hash": "0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            "is_buyer": False,
        }

        async_to_sync(Maker.objects.create)(
            user=self.user,
            amount=data["amount"],
            expiry=data["expiry"],
            price=data["price"],
            base_token=data["base_token"],
            quote_token=data["quote_token"],
            signature=data["signature"],
            order_hash=data["order_hash"],
            is_buyer=data["is_buyer"],
        )

        query = {
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        }
        response = self.client.get(reverse("api:orders"), data=query)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The order retrieving should work properly",
        )

        data["expiry"] = int(data["expiry"].timestamp())
        self.assertListEqual([data], response.json())

    def test_retrieving_own_order(self):
        """Checks that no additional data is returned on own order query"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": datetime.fromtimestamp(1696667304),
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            "order_hash": "0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            "is_buyer": False,
        }

        async_to_sync(Maker.objects.create)(
            user=self.user,
            amount=data["amount"],
            expiry=data["expiry"],
            price=data["price"],
            base_token=data["base_token"],
            quote_token=data["quote_token"],
            signature=data["signature"],
            order_hash=data["order_hash"],
            is_buyer=data["is_buyer"],
        )

        query = {
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        }

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:order"), data=query)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The own order retrieving should work properly",
        )

        data["expiry"] = int(data["expiry"].timestamp())
        self.assertListEqual([data], response.json())

    def test_sending_id_field_is_not_taken_in_account(self):
        """Checks that a user sending an id along order's field is
        not taken in account for order creation
        """
        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": datetime.fromtimestamp(1696667304),
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            "order_hash": "0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            "is_buyer": False,
        }

        async_to_sync(Maker.objects.create)(
            user=self.user,
            amount=data["amount"],
            expiry=data["expiry"],
            price=data["price"],
            base_token=data["base_token"],
            quote_token=data["quote_token"],
            signature=data["signature"],
            order_hash=data["order_hash"],
            is_buyer=data["is_buyer"],
        )

        data["id"] = 1
        data["expiry"] = "2114380800"
        data[
            "signature"
        ] = "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b"
        data[
            "order_hash"
        ] = "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6"

        response = self.client.post(reverse("api:order"), data=data)

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(response.json(), {"id": [ID_SUBMITTED_ERROR]})
