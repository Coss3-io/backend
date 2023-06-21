from decimal import Decimal
from collections import Counter
from datetime import datetime
from asgiref.sync import async_to_sync
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
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
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
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

    def test_creating_maker_order_without_address_fails(self):
        """Checks sending an order request without address fails"""

        data = {
            # "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"address": ["This field is required."]},
            "The address field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without address should fail",
        )

    def test_creating_maker_order_without_amount_fails(self):
        """Checks sending an order request without amount fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            #"amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"amount": ["This field is required."]},
            "The amount field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without amount should fail",
        )

    def test_creating_maker_order_without_expiry_fails(self):
        """Checks sending an order request without expiry fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            #"expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"expiry": ["This field is required."]},
            "The expiry field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without expiry should fail",
        )

    def test_creating_maker_order_without_price_fails(self):
        """Checks sending an order request without price fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            #"price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"price": ["This field is required."]},
            "The price field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without price should fail",
        )

    def test_creating_maker_order_without_base_token_fails(self):
        """Checks sending an order request without base_token fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            # "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"base_token": ["This field is required."]},
            "The base_token field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without base_token should fail",
        )

    def test_creating_maker_order_without_quote_token_fails(self):
        """Checks sending an order request without quote_token fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            # "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"quote_token": ["This field is required."]},
            "The quote_token field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without quote_token should fail",
        )

    def test_creating_maker_order_without_signature_fails(self):
        """Checks sending an order request without signature fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            # "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"signature": ["This field is required."]},
            "The signature field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without signature should fail",
        )

    def test_creating_maker_order_without_order_hash_fails(self):
        """Checks sending an order request without order_hash fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            # "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"order_hash": ["This field is required."]},
            "The order_hash field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without order_hash should fail",
        )

    def test_creating_maker_order_without_is_buyer_fails(self):
        """Checks sending an order request without is_buyer fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            # "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"is_buyer": ["This field is required."]},
            "The is_buyer field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without is_buyer should fail",
        )


class MakerOrderRetrievingTestCase(APITestCase):
    """Used to checks that the order retrieval works as expected"""

    def setUp(self) -> None:
        self.user_1: User = async_to_sync(User.objects.create_user)(
            address=Address("0xf17f52151EbEF6C7334FAD080c5704D77216b732")
        )

        self.user_2: User = async_to_sync(User.objects.create_user)(
            address=Address("0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef")
        )

        self.order_1_1 = {
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

        self.order_1_2 = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }

        self.order_1_3 = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("171e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("21e19")),
            "base_token": "0x3Aa5f43c7c4e2C5671A96439F1fbFfe1d58929Cb",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0x139c033404a061eae0d17dbb366f153791569d6a7ad42bc6ad7b902a341bec6d7eca9102499ff60fe566fcd53642fb254c6efa2a8ca933ba917571fbfee73d261c",
            "order_hash": "0x54532cab462b29052d84773f9f4aef6e063642c8f6d334fc4fe96394b7dbd849",
            "is_buyer": False,
        }

        self.order_2_1 = {
            "address": "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("111e16")),
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("24e19")),
            "base_token": "0x3Aa5f43c7c4e2C5671A96439F1fbFfe1d58929Cb",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0x70c8db70a8acb03fb0034eca8f9567715cd180f4a4ab313a3a76ffb490550fda61556ce93b53d5d1610d0f110626085a44860a6559187f4538012f55ef7c94e21b",
            "order_hash": "0xe114b056ec03039cf70718e911dfab7881cdd405f6da7f7e3a8254dd2ff4c75a",
            "is_buyer": True,
        }

        self.order_2_2 = {
            "address": "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("141e16")),
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("25e19")),
            "base_token": "0x3Aa5f43c7c4e2C5671A96439F1fbFfe1d58929Cb",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xeedcb0f885c0cb4dd492562c2159931ff1673184d1fdf0e052bfb84643114a1851ba73049eeb7a83d9073676be80a297c628f6c97e77f1a36f3a323ce9aa60131b",
            "order_hash": "0x9cb591205141808f11395dfbdb074d7788e3c0eb6b52af127c74e4570ba4df8a",
            "is_buyer": True,
        }

        self.order_2_3 = {
            "address": "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("182e16")),
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("27e19")),
            "base_token": "0x3Aa5f43c7c4e2C5671A96439F1fbFfe1d58929Cb",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0x04611e067ef68df5b67a58b2095a08b1c01e85bc957438cfa532090d2d067de079f532e7dde005c8de41abc0e496119a1e69d3aef9cc6715e67a44a8e626a5dc1b",
            "order_hash": "0x22bae34dd87d81f40d9643ad2143666ada40d15f55db1bb4326bc3664dbd163d",
            "is_buyer": True,
        }

        self.order_2_4 = {
            "address": "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("189e16")),
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("29e19")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0x5441d02125ed4ee031981041a5b58f45408b2a0c76205d89b7ec7e79b930a04f605f8b897433ac0f9087d3b2206395e815b2bed345f0c92be4cbdbe97c51e4f41c",
            "order_hash": "0x771a9f6d0da6256171adb5d66946f37c788b1e9117726bca6bbc5d8793db67c0",
            "is_buyer": True,
        }

        self.pair_1 = {
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        }
        self.pair_2 = {
            "base_token": "0x3Aa5f43c7c4e2C5671A96439F1fbFfe1d58929Cb",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        }
        self.pair_1_orders = [self.order_1_1, self.order_1_2, self.order_2_4]
        self.pair_2_orders = [
            self.order_1_3,
            self.order_2_1,
            self.order_2_2,
            self.order_2_3,
        ]
        self.user_1_pair_1_orders = [self.order_1_1, self.order_1_2]
        self.user_1_pair_2_orders = [
            self.order_1_3,
        ]
        self.user_2_pair_1_orders = [self.order_2_4]
        self.user_2_pair_2_orders = [
            self.order_2_1,
            self.order_2_2,
            self.order_2_3,
        ]
        self.orders = self.pair_1_orders + self.pair_2_orders

        for data in self.orders:
            async_to_sync(Maker.objects.create)(
                user=self.user_1
                if data["address"] == self.user_1.address
                else self.user_2,
                amount=data["amount"],
                expiry=datetime.fromtimestamp(data["expiry"]),
                price=data["price"],
                base_token=data["base_token"],
                quote_token=data["quote_token"],
                signature=data["signature"],
                order_hash=data["order_hash"],
                is_buyer=data["is_buyer"],
            )

    def test_retrieving_pair_1_orders_anon(self):
        """Checks retrieving all the orders for a pair works"""
        response = self.client.get(
            reverse("api:orders"),
            data=self.pair_1,
        )

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The retrieval of the orders shoul work"
        )

        self.assertListEqual(
            sorted([hash(frozenset(item.items())) for item in response.json()]),
            sorted(
                [hash(frozenset(item.items())) for item in reversed(self.pair_1_orders)]
            ),
            "The returned orders should match the orders in DB",
        )

    def test_retrieving_all_user_orders(self):
        """Checks retrieving all orders for a particular user works"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore

        response = self.client.get(reverse("api:order"), data={"all": True})

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The retrieving of all the orders should work",
        )

        self.assertListEqual(
            sorted([hash(frozenset(item.items())) for item in response.json()]),
            sorted(
                [
                    hash(frozenset(item.items()))
                    for item in reversed(
                        self.user_2_pair_2_orders + self.user_2_pair_1_orders
                    )
                ]
            ),
            "The returned user orders should match the orders in DB",
        )

    def test_retriving_user_2_pair_2_orders(self):
        """Checks retrieving specific user orders for a pair works"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(reverse("api:order"), data=self.pair_2)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The user orders for pair 2 retrieval should work properly",
        )

        self.assertListEqual(
            sorted([hash(frozenset(item.items())) for item in response.json()]),
            sorted(
                [
                    hash(frozenset(item.items()))
                    for item in reversed(self.user_2_pair_2_orders)
                ]
            ),
            "The returned user 2 pair 2 orders should match the orders in DB",
        )

    def test_anon_user_cant_see_own_orders(self):
        """An anon user should not be able to use the authenticated endpoint"""

        response = self.client.get(reverse("api:order"), data={"all": True})

        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The request should not be allowed for anonymous users",
        )

        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )
