from decimal import Decimal
from datetime import datetime
from functools import partial
from unittest.mock import patch
from datetime import datetime
from asgiref.sync import async_to_sync
from django.urls import reverse
from web3 import Web3
from django.db.utils import IntegrityError
from rest_framework import serializers
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from api.models import User
import api.errors as errors
from api.models.orders import Maker, Taker
from api.models.types import Address
from rest_framework.test import APITestCase


class MakerOrderTestCase(APITestCase):
    """Test case for creating an retrieving Maker orders"""

    def setUp(self) -> None:
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xF17f52151EbEF6C7334FAD080c5704D77216b732")
        )

    def test_creating_maker_order_works(self):
        """Checks we can create an order"""

        data = {
            "address": "0xF17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
        }
        response = self.client.post(reverse("api:order"), data=data)
        order = Maker.objects.select_related("user").get(order_hash=data["order_hash"])
        data["address"] = Web3.to_checksum_address(data["address"])
        data["bot"] = None
        self.assertDictEqual(
            data, response.json(), "The returned order should match the order sent"
        )
        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should work properly"
        )

        self.assertEqual(
            order.user.address,
            Web3.to_checksum_address(data["address"]),
            "The owner of the order should have the same address than sent",
        )

        self.assertEqual(
            order.order_hash,
            data["order_hash"],
            "The order hash should be reported on the order",
        )

        self.assertEqual(
            str(order.amount),
            data["amount"],
            "The order amount should be reported on the order",
        )

        self.assertEqual(
            str(order.price),
            data["price"],
            "The order price should be reported on the order",
        )

        self.assertEqual(
            order.base_token,
            data["base_token"],
            "The order base_token should be reported on the order",
        )

        self.assertEqual(
            order.quote_token,
            data["quote_token"],
            "The order quote_token should be reported on the order",
        )

        self.assertEqual(
            order.signature,
            data["signature"],
            "The order signature should be reported on the order",
        )

        self.assertEqual(
            int(order.expiry.timestamp()),
            data["expiry"],
            "The order expiry should be reported on the order",
        )

        self.assertEqual(
            order.is_buyer,
            data["is_buyer"],
            "The order is_buyer should be reported on the order",
        )

    def test_creating_maker_twice_fails(self):
        """Checks creating the same order twice fails"""

        data = {
            "address": "0xF17f52151EbEF6C7334FAD080c5704D77216b732",
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

        data["base_token"] = "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"
        data["quote_token"] = "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

        response = self.client.post(reverse("api:order"), data=data)
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request for a duplicate order shoud fail",
        )

        self.assertEqual(
            response.json(),
            {"order_hash": ["maker with this order hash already exists."]},
        )

    def test_creating_maker_with_0_amount_fails(self):
        """Checks we can't create an order with a 0 amount"""

        data = {
            "address": "0xF17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "0",
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xf9170415347c6ef632eb640c498ef0b1376473fd690de5a56d60cc295c8361b7724e6d7b997bef12c2d73a2eafb894cba6589686744a78c85616e594e38128351b",
            "order_hash": "0xb979428423525d098b0a9c351dff840fc31df5c71e8944f29523a243c24147d7",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a 0 amount should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"amount": [errors.Decimal.ZERO_DECIMAL_ERROR.format("amount")]},
        )

    def test_creating_an_order_with_same_base_and_quote_fails(self):
        """Checks we cannot create an order with the same base and the same quote token"""

        data = {
            "address": "0xF17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "signature": "0x415229a73d001cadbf6765dfff0ee94c67fcca3e6b6697241373aacf32e44c6218450c66d07a5ca1426244f64493a0bc83b0dbdab9e5a72dfe43d26eb96cf82f1c",
            "order_hash": "0x20126b2fcf1333c5efd0a330741e587f527573980114eb983fbeba0afc58e4a6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Order.SAME_BASE_QUOTE_ERROR]},
            "The order creation should fail with same base and same quote token",
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the response status code should be 400",
        )

    def test_creating_an_order_with_same_base_and_quote_different_case_fails(self):
        """
        Checks we cannot create an order with the same base
        and the same quote token but with different cases fails
        """

        data = {
            "address": "0xF17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0xf25186b5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "signature": "0x415229a73d001cadbf6765dfff0ee94c67fcca3e6b6697241373aacf32e44c6218450c66d07a5ca1426244f64493a0bc83b0dbdab9e5a72dfe43d26eb96cf82f1c",
            "order_hash": "0x20126b2fcf1333c5efd0a330741e587f527573980114eb983fbeba0afc58e4a6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Order.SAME_BASE_QUOTE_ERROR]},
            "The order creation should fail with same base and same quote token",
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the response status code should be 400",
        )

    def test_creating_an_order_without_user_or_bot_should_fail(self):
        """Checks the creation of an order need at bot or user"""

        self.assertRaises(
            IntegrityError,
            partial(
                async_to_sync(Maker.objects.create),
                amount="1",
                expiry=datetime.fromtimestamp(2114380800),
                price="1",
                base_token="0xf17f52151EbEF6C7334FAD080c5704D77216b732",
                quote_token="0xf17f52151EbEF6C7334FAD080c5704D77216b731",
                signature="0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
                order_hash="0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
                is_buyer=False,
            ),
        )

    def test_retrieve_maker_orders_anon(self):
        """checks we ca retrieve the maker orders being anon"""

        data = {
            "address": "0xf17f52151EBEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": datetime.fromtimestamp(1696667304),
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            "order_hash": "0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
        }

        async_to_sync(Maker.objects.create)(
            user=self.user,
            amount=data["amount"],
            expiry=data["expiry"],
            price=data["price"],
            base_token=Web3.to_checksum_address(data["base_token"]),
            quote_token=Web3.to_checksum_address(data["quote_token"]),
            signature=data["signature"],
            order_hash=data["order_hash"],
            is_buyer=data["is_buyer"],
        )

        query = {
            "base_token": "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756CC2",
        }
        response = self.client.get(reverse("api:orders"), data=query)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The order retrieving should work properly",
        )
        data["bot"] = None
        data["expiry"] = int(data["expiry"].timestamp())
        data["address"] = Web3.to_checksum_address(data["address"])
        data["base_token"] = Web3.to_checksum_address(data["base_token"])
        data["quote_token"] = Web3.to_checksum_address(data["quote_token"])
        self.assertListEqual([data], response.json())

    def test_retrieving_own_order(self):
        """Checks that no additional data is returned on own order query"""

        data = {
            "address": "0xf17f52151EBEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": datetime.fromtimestamp(1696667304),
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            "order_hash": "0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            "is_buyer": False,
            "filled": "0",
            "status": "OPEN",
            "base_fees": "0",
            "quote_fees": "0",
        }

        async_to_sync(Maker.objects.create)(
            user=self.user,
            amount=data["amount"],
            expiry=data["expiry"],
            price=data["price"],
            base_token=Web3.to_checksum_address(data["base_token"]),
            quote_token=Web3.to_checksum_address(data["quote_token"]),
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
        data["bot"] = None
        data["expiry"] = int(data["expiry"].timestamp())
        data["address"] = Web3.to_checksum_address(data["address"])
        data["base_token"] = Web3.to_checksum_address(data["base_token"])
        data["quote_token"] = Web3.to_checksum_address(data["quote_token"])
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
        self.assertDictEqual(response.json(), {"id": [errors.Order.ID_SUBMITTED_ERROR]})

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
            {"address": [errors.General.MISSING_FIELD]},
            "The address field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without address should fail",
        )

    def test_creating_maker_order_with_wrong_address_fails(self):
        """Checks sending an order request with wrong address fails"""

        data = {
            "address": "0xz17f52151EbEF6C7334FAD080c5704D77216b732",
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
            {"address": [errors.Address.WRONG_ADDRESS_ERROR.format("")]},
            "The address field should be valid",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with wrong address should fail",
        )

    def test_creating_maker_order_with_short_address_fails(self):
        """Checks sending an order request with short address fails"""

        data = {
            "address": "0x17f52151EbEF6C7334FAD080c5704D77216b732",
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
            {"address": [errors.Address.SHORT_ADDRESS_ERROR.format("")]},
            "The address field should be 42 chars length",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with short address should fail",
        )

    def test_creating_maker_order_with_long_address_fails(self):
        """Checks sending an order request with long address fails"""

        data = {
            "address": "0xff17f52151EbEF6C7334FAD080c5704D77216b732",
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
            {"address": [errors.Address.LONG_ADDRESS_ERROR.format("")]},
            "The address field should be 42 chars length",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with long address should fail",
        )

    def test_creating_maker_order_without_amount_fails(self):
        """Checks sending an order request without amount fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            # "amount": "{0:f}".format(Decimal("173e16")),
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
            {"amount": [errors.General.MISSING_FIELD]},
            "The amount field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without amount should fail",
        )

    def test_creating_maker_order_with_wrong_amount_fails(self):
        """Checks sending an order request with wrong amount fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "a" + "{0:f}".format(Decimal("173e16")),
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
            {"amount": [serializers.DecimalField.default_error_messages["invalid"]]},
            "The amount field should be valid",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with wrong amount should fail",
        )

    def test_creating_maker_order_without_expiry_fails(self):
        """Checks sending an order request without expiry fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            # "expiry": 2114380800,
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

    def test_creating_maker_order_with_wrong_expiry_fails(self):
        """Checks sending an order request with wrong expiry fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": "2114380800a",
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
            {"expiry": [errors.Decimal.WRONG_DECIMAL_ERROR.format("expiry")]},
            "The expiry field should be valid",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with wrong expiry should fail",
        )

    def test_creating_maker_order_without_price_fails(self):
        """Checks sending an order request without price fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            # "price": "{0:f}".format(Decimal("2e20")),
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

    def test_creating_maker_order_with_wrong_price_fails(self):
        """Checks sending an order request with wrong price fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "a" + "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"price": [serializers.DecimalField.default_error_messages["invalid"]]},
            "The price field should be valid",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with wrong price should fail",
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

    def test_creating_maker_order_with_wrong_base_token_fails(self):
        """Checks sending an order request with wrong base_token fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0xzbbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"base_token": [errors.Address.WRONG_ADDRESS_ERROR.format("base_token")]},
            "The base_token field should be valid",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with wrong base_token should fail",
        )

    def test_creating_maker_order_with_short_base_token_fails(self):
        """Checks sending an order request with short base_token fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0xbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {
                "base_token": [
                    serializers.CharField.default_error_messages.get(
                        "min_length", ""
                    ).format(min_length=42)
                ]
            },
            "The base_token field should not be less than 42 chars",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with short base_token should fail",
        )

    def test_creating_maker_order_with_long_base_token_fails(self):
        """Checks sending an order request with long base_token fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0xffbbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {
                "base_token": [
                    serializers.CharField.default_error_messages.get(
                        "max_length", ""
                    ).format(max_length=42)
                ]
            },
            "The base_token field should not be more than 42 chars",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with long base_token should fail",
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
            {"quote_token": [errors.General.MISSING_FIELD]},
            "The quote_token field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without quote_token should fail",
        )

    def test_creating_maker_order_with_wrong_quote_token_fails(self):
        """Checks sending an order request with wrong quote_token fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xZ02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"quote_token": [errors.Address.WRONG_ADDRESS_ERROR.format("quote_token")]},
            "The quote_token field should be valid",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with wrong quote_token should fail",
        )

    def test_creating_maker_order_with_short_quote_token_fails(self):
        """Checks sending an order request with short quote_token fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0x02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {
                "quote_token": [
                    serializers.CharField.default_error_messages.get(
                        "min_length", ""
                    ).format(min_length=42)
                ]
            },
            "The quote_token field should not be less than 42 chars",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with short quote_token should fail",
        )

    def test_creating_maker_order_with_long_quote_token_fails(self):
        """Checks sending an order request with long quote_token fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xCC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {
                "quote_token": [
                    serializers.CharField.default_error_messages.get(
                        "max_length", ""
                    ).format(max_length=42)
                ]
            },
            "The quote_token field should not be more than 42 chars",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with long quote_token should fail",
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
            {"signature": [errors.General.MISSING_FIELD]},
            "The signature field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without signature should fail",
        )

    def test_creating_maker_order_with_wrong_signature_fails(self):
        """Checks sending an order request with wrong signature fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xz49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"signature": [errors.Signature.WRONG_SIGNATURE_ERROR]},
            "The signature field should be valid",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with wrong signature should fail",
        )

    def test_creating_maker_order_with_mismatch_signature_fails(self):
        """Checks sending an order request with mismatch signature fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1d",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Signature.SIGNATURE_MISMATCH_ERROR]},
            "The signature field should be valid",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with mismatch signature should fail",
        )

    def test_creating_maker_order_with_short_signature_fails(self):
        """Checks sending an order request with short signature fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0x49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {
                "signature": [
                    serializers.CharField.default_error_messages.get(
                        "min_length", ""
                    ).format(min_length=132)
                ]
            },
            "The signature field should not be less than 132",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with short signature should fail",
        )

    def test_creating_maker_order_with_long_signature_fails(self):
        """Checks sending an order request with long signature fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xcc49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {
                "signature": [
                    serializers.CharField.default_error_messages.get(
                        "max_length", ""
                    ).format(max_length=132)
                ]
            },
            "The signature field should not be more than 132",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with long signature should fail",
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
            {"order_hash": [errors.General.MISSING_FIELD]},
            "The order_hash field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without order_hash should fail",
        )

    def test_creating_maker_order_mismatch_order_hash_fails(self):
        """Checks sending an order request mismatch order_hash fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2b156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"error": [errors.KeccakHash.MISMATCH_HASH_ERROR]},
            "The order_hash computed should match the order hash sent",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without order_hash should fail",
        )

    def test_creating_maker_order_with_wrong_order_hash_fails(self):
        """Checks sending an order request with wrong order_hash fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0xZa156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"order_hash": [errors.KeccakHash.WRONG_HASH_ERROR]},
            "The order_hash field should be valid",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with wrong order_hash should fail",
        )

    def test_creating_maker_order_with_short_order_hash_fails(self):
        """Checks sending an order request with short order_hash fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {
                "order_hash": [
                    serializers.CharField.default_error_messages.get(
                        "min_length", "{}"
                    ).format(min_length="66")
                ]
            },
            "The order_hash field should not be less than 42 chars",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with short order_hash should fail",
        )

    def test_creating_maker_order_with_long_order_hash_fails(self):
        """Checks sending an order request with long order_hash fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2aa156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {
                "order_hash": [
                    serializers.CharField.default_error_messages.get(
                        "max_length", "{}"
                    ).format(max_length="66")
                ]
            },
            "The order_hash field should not be more than 42 chars",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with long order_hash should fail",
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
            {"is_buyer": [errors.General.MISSING_FIELD]},
            "The is_buyer field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without is_buyer should fail",
        )

    def test_creating_maker_order_with_wrong_is_buyer_fails(self):
        """Checks sending an order request with wrong is_buyer fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": "Fgrtalse",
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"is_buyer": [serializers.BooleanField.default_error_messages["invalid"]]},
            "The is_buyer field should be valid",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with wrong is_buyer should fail",
        )

    def test_user_creation_on_order_request(self):
        """Checks user creation works well on unregistered user order"""

        data = {
            "address": "0xC5FDF4076b8F3A5357c5E395ab970B5B54098FEF",
            "amount": "{0:f}".format(Decimal("189e16")),
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("28e19")),
            "base_token": "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0x9cc2023e1b0401282c9b8abb371e09f4ef5cf4ff54d08bdfb9bb6d05f14a70f36de2002f2f005cd3dfb5ae42d023b18010a4a234d3ce8ed5b915d0fcb40c4ed91b",
            "order_hash": "0xddd97cfb8a661a4d513c78874c0ef707909f9a07fcd80d5aa147cbd23dae0aa6",
            "is_buyer": True,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
        }
        response = self.client.post(reverse("api:order"), data=data)
        User.objects.get(address=Web3.to_checksum_address(data["address"]))

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The order resquest should not fail"
        )

        data["bot"] = None
        data["address"] = Web3.to_checksum_address(data["address"])
        data["base_token"] = Web3.to_checksum_address(data["base_token"])
        data["quote_token"] = Web3.to_checksum_address(data["quote_token"])

        self.assertDictEqual(
            response.json(), data, "The returned data should match the data sent"
        )


class MakerOrderRetrievingTestCase(APITestCase):
    """Used to checks that the order retrieval works as expected"""

    def setUp(self) -> None:
        self.user_1: User = async_to_sync(User.objects.create_user)(
            address=Address(
                Web3.to_checksum_address("0xF17f52151EbEF6C7334FAD080c5704D77216b732")
            )
        )

        self.user_2: User = async_to_sync(User.objects.create_user)(
            address=Address(
                Web3.to_checksum_address("0xC5FDF4076b8F3A5357c5E395ab970B5B54098Fef")
            )
        )

        self.user_3: User = async_to_sync(User.objects.create_user)(
            address=Address(
                Web3.to_checksum_address("0xC6FDF4076b8F3A5357c5E395ab970B5B54098Fef")
            )
        )

        self.order_1_1 = {
            "address": Web3.to_checksum_address(
                "0xf17f52151EbEF6C7334FAD080c5704D77216B732"
            ),
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 1696667304,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": Web3.to_checksum_address(
                "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"
            ),
            "quote_token": Web3.to_checksum_address(
                "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            ),
            "signature": "0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            "order_hash": "0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None
        }

        self.order_1_2 = {
            "address": Web3.to_checksum_address(
                "0xf17f52151Ebef6C7334FAD080c5704D77216b732"
            ),
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": Web3.to_checksum_address(
                "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"
            ),
            "quote_token": Web3.to_checksum_address(
                "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            ),
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None
        }

        self.order_1_3 = {
            "address": Web3.to_checksum_address(
                "0xf17f52151Ebef6C7334FAD080c5704D77216b732"
            ),
            "amount": "{0:f}".format(Decimal("171e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("21e19")),
            "base_token": Web3.to_checksum_address(
                "0x3Aa5f43c7C4e2C5671A96439F1fbFfe1d58929Cb"
            ),
            "quote_token": Web3.to_checksum_address(
                "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            ),
            "signature": "0x139c033404a061eae0d17dbb366f153791569d6a7ad42bc6ad7b902a341bec6d7eca9102499ff60fe566fcd53642fb254c6efa2a8ca933ba917571fbfee73d261c",
            "order_hash": "0x54532cab462b29052d84773f9f4aef6e063642c8f6d334fc4fe96394b7dbd849",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None
        }

        self.order_2_1 = {
            "address": Web3.to_checksum_address(
                "0xC5FDF4076b8F3A5357c5E395ab970B5B54098Fef"
            ),
            "amount": "{0:f}".format(Decimal("111e16")),
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("24e19")),
            "base_token": Web3.to_checksum_address(
                "0x3AA5f43c7c4e2C5671A96439F1fbFfe1d58929Cb"
            ),
            "quote_token": Web3.to_checksum_address(
                "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            ),
            "signature": "0x346d7e67d76b8de75de2c18855818261394323565f0c246bd565ec448f670fa91c3139086f11ef6853fcae56cd67d89cbf4f60916898579836dec681b7f9249d1c",
            "order_hash": "0x07f5c2584ffbf3b7d14ad3410c1c98fb3b71496a7e5cd14ab22a68f268915bca",
            "is_buyer": True,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None
        }

        self.order_2_2 = {
            "address": Web3.to_checksum_address(
                "0xC5FDF4076b8F3A5357c5E395ab970B5B54098Fef"
            ),
            "amount": "{0:f}".format(Decimal("141e16")),
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("25e19")),
            "base_token": Web3.to_checksum_address(
                "0x3AA5f43c7c4e2C5671A96439F1fbFfe1d58929Cb"
            ),
            "quote_token": Web3.to_checksum_address(
                "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            ),
            "signature": "0xee7433f9f83b59019723f08c8348895a767eb1aae16536847b54de37b3e92ff93f916e4c302309b7317335c9f9aad8e18927371994ef08ce75d8357376e2ef0a1b",
            "order_hash": "0x43a67aa1f3e53cad7f692f2ac249728f3369290b24a154e364c998fc9788b98f",
            "is_buyer": True,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None
        }

        self.order_2_3 = {
            "address": Web3.to_checksum_address(
                "0xC5FDF4076b8F3A5357c5E395ab970B5B54098Fef"
            ),
            "amount": "{0:f}".format(Decimal("182e16")),
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("27e19")),
            "base_token": Web3.to_checksum_address(
                "0x3AA5f43c7c4e2C5671A96439F1fbFfe1d58929Cb"
            ),
            "quote_token": Web3.to_checksum_address(
                "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            ),
            "signature": "0x69b2da58758a256e2d24a6f04ca5d8dc7d4834b96a6246e18c2b9e8ecba80992145267c18e8add3a7b952121a9ae82ad090fc05ba44688f445e54a5b21caa6a81b",
            "order_hash": "0xa8a829d6e7ad540c0d3140a37e9fb9408878e5b5b5d7d48e54ba132a5c968e6a",
            "is_buyer": True,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None
        }

        self.order_2_4 = {
            "address": Web3.to_checksum_address(
                "0xC5FDF4076b8F3A5357c5E395ab970B5B54098Fef"
            ),
            "amount": "{0:f}".format(Decimal("189e16")),
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("29e19")),
            "base_token": Web3.to_checksum_address(
                "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"
            ),
            "quote_token": Web3.to_checksum_address(
                "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            ),
            "signature": "0x422b8570187908abb3a18a2f224e7fa4870c18944f9b4b86bc4b498c738739b90e6db92a52b994920908d64404482856226065001156ca2dbbe6b330d31116811b",
            "order_hash": "0x37ec83d93794625c87faa2aa937c3582bd310a147d019f7d1d56bc24b04d45ef",
            "is_buyer": True,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None
        }

        self.pair_1 = {
            "base_token": "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        }
        self.pair_2 = {
            "base_token": "0x3AA5f43c7c4e2C5671A96439f1fbFfe1d58929Cb",
            "quote_token": "0xC02AAA39b223FE8D0A0E5C4F27eAD9083C756Cc2",
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
                base_token=Web3.to_checksum_address(data["base_token"]),
                quote_token=Web3.to_checksum_address(data["quote_token"]),
                signature=data["signature"],
                order_hash=data["order_hash"],
                is_buyer=data["is_buyer"],
            )

    def test_retrieving_auth_no_orders_works(self):
        """Checks the empty order retrieval works"""

        self.client.force_authenticate(user=self.user_3)  # type: ignore
        response = self.client.get(reverse("api:order"), data={"all": True})

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The request even if the user has no orders should work",
        )
        self.assertListEqual(
            response.json(), [], "The returned order list should be empty for the user"
        )

    def test_retrieving_anon_no_orders_works(self):
        """Checks the anon empty order retrieval works"""

        Maker.objects.all().delete()
        response = self.client.get(
            reverse("api:orders"),
            data=self.pair_1,
        )

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The request even if the user has no orders should work",
        )
        self.assertListEqual(
            response.json(), [], "The returned order list should be empty for the user"
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

    def test_getting_own_orders_no_params_fails(self):
        """Checks getting user own order with no get parameters fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(reverse("api:order"), data={})

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without parameters should fail",
        )

        self.assertDictEqual(
            response.json(), {"detail": "base_token and quote_token params are needed"}
        )

    def test_getting_own_orders_without_base_token(self):
        """Checks getting own orders without base_token params fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"), data={"quote_token": self.pair_2["quote_token"]}
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without base_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(), {"detail": "base_token and quote_token params are needed"}
        )

    def test_getting_own_orders_without_quote_token(self):
        """Checks getting own orders without base_token params fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"), data={"base_token": self.pair_2["base_token"]}
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without quote_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(), {"detail": "base_token and quote_token params are needed"}
        )

    def test_getting_own_orders_wrong_base_token(self):
        """Checks getting own orders with wrong base token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={
                "base_token": "0xZ02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "quote_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with wrong base_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"base_token": [errors.Address.WRONG_ADDRESS_ERROR.format("base_token")]},
        )

    def test_getting_own_orders_wrong_quote_token(self):
        """Checks getting own orders with wrong quote token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={
                "quote_token": "0xZ02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "base_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with wrong quote_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"quote_token": [errors.Address.WRONG_ADDRESS_ERROR.format("quote_token")]},
        )

    def test_getting_own_orders_short_base_token(self):
        """Checks getting own orders with short base token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={
                "base_token": "0x02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "quote_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with short base_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"base_token": [errors.Address.SHORT_ADDRESS_ERROR.format("base_token")]},
        )

    def test_getting_own_orders_short_quote_token(self):
        """Checks getting own orders with short quote token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={
                "quote_token": "0x02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "base_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with short quote_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"quote_token": [errors.Address.SHORT_ADDRESS_ERROR.format("quote_token")]},
        )

    def test_getting_own_orders_long_base_token(self):
        """Checks getting own orders with long base token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={
                "base_token": "0xAA02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "quote_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with long base_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"base_token": [errors.Address.LONG_ADDRESS_ERROR.format("base_token")]},
        )

    def test_getting_own_orders_long_quote_token(self):
        """Checks getting own orders with long quote token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={
                "quote_token": "0xAA02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "base_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with long quote_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"quote_token": [errors.Address.LONG_ADDRESS_ERROR.format("quote_token")]},
        )

    def test_getting_general_orders_without_base_token(self):
        """Checks getting genral orders without base_token params fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:orders"), data={"quote_token": self.pair_2["quote_token"]}
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without base_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(), {"detail": "base_token and quote_token params are needed"}
        )

    def test_getting_general_orders_without_quote_token(self):
        """Checks getting general orders without base_token params fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:orders"), data={"base_token": self.pair_2["base_token"]}
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without quote_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(), {"detail": "base_token and quote_token params are needed"}
        )

    def test_getting_general_orders_wrong_base_token(self):
        """Checks getting general orders with wrong base token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:orders"),
            data={
                "base_token": "0xZ02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "quote_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with wrong base_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"base_token": [errors.Address.WRONG_ADDRESS_ERROR.format("base_token")]},
        )

    def test_getting_general_orders_wrong_quote_token(self):
        """Checks getting general orders with wrong quote token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:orders"),
            data={
                "quote_token": "0xZ02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "base_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with wrong quote_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"quote_token": [errors.Address.WRONG_ADDRESS_ERROR.format("quote_token")]},
        )

    def test_getting_general_orders_short_base_token(self):
        """Checks getting general orders with short base token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:orders"),
            data={
                "base_token": "0x02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "quote_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with short base_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"base_token": [errors.Address.SHORT_ADDRESS_ERROR.format("base_token")]},
        )

    def test_getting_general_orders_short_quote_token(self):
        """Checks getting general orders with short quote token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:orders"),
            data={
                "quote_token": "0x02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "base_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with short quote_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"quote_token": [errors.Address.SHORT_ADDRESS_ERROR.format("quote_token")]},
        )

    def test_getting_general_orders_long_base_token(self):
        """Checks getting general orders with long base token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:orders"),
            data={
                "base_token": "0xAA02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "quote_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with long base_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"base_token": [errors.Address.LONG_ADDRESS_ERROR.format("base_token")]},
        )

    def test_getting_general_orders_long_quote_token(self):
        """Checks getting general orders with long quote token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:orders"),
            data={
                "quote_token": "0xAA02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "base_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with long quote_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"quote_token": [errors.Address.LONG_ADDRESS_ERROR.format("quote_token")]},
        )


class MakerAPILogInTestCase(APITestCase):
    """Class used to check the API authentication works"""

    def test_regular_API_log_in_works(self):
        """Checks the api log in work"""
        signature = "0x2d11ff301b38ac81e95bc3bbf70055ba7352a786aacbbbff2753200343010000519a3d6d33077de548b66f8f18c40450b97259df914d5999a3cc9f7131d7829b1b"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = 2114380800

        with patch("api.utils.time", return_value=2114380800):
            response = self.client.get(
                reverse("api:order"),
                data={
                    "all": True,
                    "signature": signature,
                    "address": address,
                    "timestamp": timestamp,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "the request with right log in should work",
        )
        self.assertEqual(
            response.json(), [], "The response should not contain any orders"
        )

    def test_API_log_in_no_timestamp(self):
        """Checks the API log in fails without timestamp param"""

        signature = "0x2d11ff301b38ac81e95bc3bbf70055ba7352a786aacbbbff2753200343010000519a3d6d33077de548b66f8f18c40450b97259df914d5999a3cc9f7131d7829b1b"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = 2114380800

        with patch("api.utils.time", return_value=2114380800):
            response = self.client.get(
                reverse("api:order"),
                data={
                    "all": True,
                    "signature": signature,
                    "address": address,
                    # "timestamp": timestamp,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The request without being authenticated should be rejected",
        )

        self.assertDictEqual(
            response.json(),
            {"timestamp": [errors.General.MISSING_FIELD.format("timestamp")]},
        )

    def test_API_log_in_wrong_timestamp(self):
        """Checks the API log in fails with wrong timestamp param"""

        signature = "0x2d11ff301b38ac81e95bc3bbf70055ba7352a786aacbbbff2753200343010000519a3d6d33077de548b66f8f18c40450b97259df914d5999a3cc9f7131d7829b1b"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = "a2114380800"

        with patch("api.utils.time", return_value=2114380800):
            response = self.client.get(
                reverse("api:order"),
                data={
                    "all": True,
                    "signature": signature,
                    "address": address,
                    "timestamp": timestamp,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The request without being authenticated should be rejected",
        )

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Decimal.WRONG_DECIMAL_ERROR.format("timestamp")]},
        )

    def test_regular_API_log_in_wrogn_signature(self):
        """Checks the api log in fails with wrong signature"""
        signature = "0x3d11ff301b38ac81e95bc3bbf70055ba7352a786aacbbbff2753200343010000519a3d6d33077de548b66f8f18c40450b97259df914d5999a3cc9f7131d7829b1b"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = 2114380800

        with patch("api.utils.time", return_value=2114380800):
            response = self.client.get(
                reverse("api:order"),
                data={
                    "all": True,
                    "signature": signature,
                    "address": address,
                    "timestamp": timestamp,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "the resquest with a wrong signature should not be authenticated",
        )

        self.assertDictEqual(
            response.json(), {"signature": [errors.Signature.SIGNATURE_MISMATCH_ERROR]}
        )


class MakerTakersFeesRetrieval(APITestCase):
    """Checks the maker fees retrieval works when trades have been make"""

    def setUp(self):
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xf17f52151EbEF6C7334FAD080c5704D77216b732")
        )
        self.taker_user = async_to_sync(User.objects.create_user)(
            address=Address("0xf18f52151EbEF6C7334FAD080c5704D77216b732")
        )

        self.data = {
            "address": Web3.to_checksum_address(
                "0xf17f52151EbEF6C7334FAD080c5704D77216B732"
            ),
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 1696667304,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": Web3.to_checksum_address(
                "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"
            ),
            "quote_token": Web3.to_checksum_address(
                "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            ),
            "signature": "0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            "order_hash": "0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
        }

        self.maker = async_to_sync(Maker.objects.create)(
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

    def test_maker_w_one_base_fees_taker(self):
        """Checks a maker with one taker order with base
        fees is well returned
        """

        taker_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": True,
            "fees": Decimal("121e16"),
            "is_buyer": True,
        }

        async_to_sync(Taker.objects.create)(
            taker_amount=taker_details["taker_amount"],
            maker=taker_details["maker"],
            user=taker_details["user"],
            block=taker_details["block"],
            base_fees=taker_details["base_fees"],
            fees=taker_details["fees"],
            is_buyer=taker_details["is_buyer"],
        )

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:order"), data={"all": True})

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should work fine"
        )
        self.assertEqual(
            response.json()[0]["base_fees"],
            "{0:f}".format(taker_details["fees"]),
            "The base fees amount returned should match the taker base fees",
        )
        self.assertEqual(
            response.json()[0]["quote_fees"],
            "0",
            "No quote fees should be returned",
        )

    def test_maker_w_two_base_takers(self):
        """Checks a maker with two taker orders is well returned"""
        taker_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": True,
            "fees": Decimal("121e16"),
            "is_buyer": True,
        }

        taker2_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": True,
            "fees": Decimal("145e16"),
            "is_buyer": True,
        }

        async_to_sync(Taker.objects.create)(
            taker_amount=taker_details["taker_amount"],
            maker=taker_details["maker"],
            user=taker_details["user"],
            block=taker_details["block"],
            base_fees=taker_details["base_fees"],
            fees=taker_details["fees"],
            is_buyer=taker_details["is_buyer"],
        )

        async_to_sync(Taker.objects.create)(
            taker_amount=taker2_details["taker_amount"],
            maker=taker2_details["maker"],
            user=taker2_details["user"],
            block=taker2_details["block"],
            base_fees=taker2_details["base_fees"],
            fees=taker2_details["fees"],
            is_buyer=taker2_details["is_buyer"],
        )

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:order"), data={"all": True})

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should work fine"
        )
        self.assertEqual(
            response.json()[0]["base_fees"],
            "{0:f}".format(taker_details["fees"] + taker2_details["fees"]),
            "The base fees amount returned should match the two takers base fees",
        )
        self.assertEqual(
            response.json()[0]["quote_fees"],
            "0",
            "No quote fees should be returned",
        )

    def test_maker_w_one_quote_taker(self):
        """Checks a maker with one quote taker is well returned"""
        taker_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": False,
            "fees": Decimal("121e16"),
            "is_buyer": True,
        }

        async_to_sync(Taker.objects.create)(
            taker_amount=taker_details["taker_amount"],
            maker=taker_details["maker"],
            user=taker_details["user"],
            block=taker_details["block"],
            base_fees=taker_details["base_fees"],
            fees=taker_details["fees"],
            is_buyer=taker_details["is_buyer"],
        )

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:order"), data={"all": True})

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should work fine"
        )
        self.assertEqual(
            response.json()[0]["quote_fees"],
            "{0:f}".format(taker_details["fees"]),
            "The quote fees amount returned should match the taker quote fees",
        )
        self.assertEqual(
            response.json()[0]["base_fees"],
            "0",
            "No base fees should be returned",
        )

    def test_maker_w_two_quote_takers(self):
        """Checks a make with two quote takers is well handled"""

        taker_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": False,
            "fees": Decimal("121e16"),
            "is_buyer": True,
        }

        taker2_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": False,
            "fees": Decimal("145e16"),
            "is_buyer": True,
        }

        async_to_sync(Taker.objects.create)(
            taker_amount=taker_details["taker_amount"],
            maker=taker_details["maker"],
            user=taker_details["user"],
            block=taker_details["block"],
            base_fees=taker_details["base_fees"],
            fees=taker_details["fees"],
            is_buyer=taker_details["is_buyer"],
        )

        async_to_sync(Taker.objects.create)(
            taker_amount=taker2_details["taker_amount"],
            maker=taker2_details["maker"],
            user=taker2_details["user"],
            block=taker2_details["block"],
            base_fees=taker2_details["base_fees"],
            fees=taker2_details["fees"],
            is_buyer=taker2_details["is_buyer"],
        )

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:order"), data={"all": True})

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should work fine"
        )
        self.assertEqual(
            response.json()[0]["quote_fees"],
            "{0:f}".format(taker_details["fees"] + taker2_details["fees"]),
            "The quote fees amount returned should match the two takers quote fees",
        )
        self.assertEqual(
            response.json()[0]["base_fees"],
            "0",
            "No base fees should be returned",
        )

    def test_maker_w_one_quote_and_base_taker(self):
        """Checks a maker with base and quote takers is well returned"""
        taker_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": True,
            "fees": Decimal("121e16"),
            "is_buyer": True,
        }

        taker2_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": False,
            "fees": Decimal("145e16"),
            "is_buyer": True,
        }

        async_to_sync(Taker.objects.create)(
            taker_amount=taker_details["taker_amount"],
            maker=taker_details["maker"],
            user=taker_details["user"],
            block=taker_details["block"],
            base_fees=taker_details["base_fees"],
            fees=taker_details["fees"],
            is_buyer=taker_details["is_buyer"],
        )

        async_to_sync(Taker.objects.create)(
            taker_amount=taker2_details["taker_amount"],
            maker=taker2_details["maker"],
            user=taker2_details["user"],
            block=taker2_details["block"],
            base_fees=taker2_details["base_fees"],
            fees=taker2_details["fees"],
            is_buyer=taker2_details["is_buyer"],
        )

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:order"), data={"all": True})

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should work fine"
        )
        self.assertEqual(
            response.json()[0]["base_fees"],
            "{0:f}".format(taker_details["fees"]),
            "The base fees amount returned should match the base taker fees",
        )
        self.assertEqual(
            response.json()[0]["quote_fees"],
            "{0:f}".format(taker2_details["fees"]),
            "The quote fees returned should match the quote taker fees",
        )

    def test_maker_w_two_quote_and_base_takers(self):
        """Checks a maker with base and quote takers is well returned"""
        taker_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": True,
            "fees": Decimal("121e16"),
            "is_buyer": True,
        }

        taker2_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": True,
            "fees": Decimal("145e16"),
            "is_buyer": True,
        }

        taker3_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": False,
            "fees": Decimal("15e16"),
            "is_buyer": True,
        }

        taker4_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": False,
            "fees": Decimal("185e16"),
            "is_buyer": True,
        }

        for taker in [taker_details, taker2_details, taker3_details, taker4_details]:
            async_to_sync(Taker.objects.create)(
                taker_amount=taker["taker_amount"],
                maker=taker["maker"],
                user=taker["user"],
                block=taker["block"],
                base_fees=taker["base_fees"],
                fees=taker["fees"],
                is_buyer=taker["is_buyer"],
            )

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:order"), data={"all": True})

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should work fine"
        )
        self.assertEqual(
            response.json()[0]["base_fees"],
            "{0:f}".format(taker_details["fees"] + taker2_details["fees"]),
            "The base fees amount returned should match the base taker fees",
        )
        self.assertEqual(
            response.json()[0]["quote_fees"],
            "{0:f}".format(taker3_details["fees"] + taker4_details["fees"]),
            "The quote fees returned should match the quote taker fees",
        )

    def test_two_makers_w_two_quote_and_base_takers(self):
        """Checks two maker with base and quote taker are well returned"""

        self.data = {
            "address": Web3.to_checksum_address(
                "0xf17f52151Ebef6C7334FAD080c5704D77216b732"
            ),
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": Web3.to_checksum_address(
                "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"
            ),
            "quote_token": Web3.to_checksum_address(
                "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            ),
            "signature": "0xd49cd61bc7ee3aa1ee3f885d6d32b0d8bc5557b3435b80930cf78f02f537d2fd2da54b7521f3ae9b9fd0cca59d16bcbfeb8ec3f229419624386e812ae8a15d5e1b",
            "order_hash": "0x2a156142f5aa7c8897012964f808fdf5057259bec4d47874d8d40189087069b6",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
        }

        maker2 = async_to_sync(Maker.objects.create)(
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

        taker_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": True,
            "fees": Decimal("121e16"),
            "is_buyer": True,
        }

        taker2_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": True,
            "fees": Decimal("145e16"),
            "is_buyer": True,
        }

        taker3_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": False,
            "fees": Decimal("15e16"),
            "is_buyer": True,
        }

        taker4_details = {
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": False,
            "fees": Decimal("185e16"),
            "is_buyer": True,
        }

        taker2_1_details = {
            "taker_amount": Decimal("12e17"),
            "maker": maker2,
            "user": self.taker_user,
            "block": 18,
            "base_fees": True,
            "fees": Decimal("1e16"),
            "is_buyer": True,
        }

        taker2_2_details = {
            "taker_amount": Decimal("12e17"),
            "maker": maker2,
            "user": self.taker_user,
            "block": 18,
            "base_fees": True,
            "fees": Decimal("5e16"),
            "is_buyer": True,
        }

        taker2_3_details = {
            "taker_amount": Decimal("12e17"),
            "maker": maker2,
            "user": self.taker_user,
            "block": 18,
            "base_fees": False,
            "fees": Decimal("2e16"),
            "is_buyer": True,
        }

        taker2_4_details = {
            "taker_amount": Decimal("12e17"),
            "maker": maker2,
            "user": self.taker_user,
            "block": 18,
            "base_fees": False,
            "fees": Decimal("8e16"),
            "is_buyer": True,
        }

        for taker in [
            taker_details,
            taker2_details,
            taker3_details,
            taker4_details,
            taker2_1_details,
            taker2_2_details,
            taker2_3_details,
            taker2_4_details,
        ]:
            async_to_sync(Taker.objects.create)(
                taker_amount=taker["taker_amount"],
                maker=taker["maker"],
                user=taker["user"],
                block=taker["block"],
                base_fees=taker["base_fees"],
                fees=taker["fees"],
                is_buyer=taker["is_buyer"],
            )

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:order"), data={"all": True})

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should work fine"
        )

        data = response.json()
        if data[0]["order_hash"] == self.maker.order_hash:
            maker_1, maker_2 = data[0], data[1]
        else:
            maker_1, maker_2 = data[1], data[0]

        self.assertEqual(
            maker_1["base_fees"],
            "{0:f}".format(taker_details["fees"] + taker2_details["fees"]),
            "The base fees amount returned should match the base taker fees",
        )
        self.assertEqual(
            maker_1["quote_fees"],
            "{0:f}".format(taker3_details["fees"] + taker4_details["fees"]),
            "The quote fees returned should match the quote taker fees",
        )

        self.assertEqual(
            maker_2["base_fees"],
            "{0:f}".format(taker2_1_details["fees"] + taker2_2_details["fees"]),
            "The base fees amount returned should match the base taker fees",
        )
        self.assertEqual(
            maker_2["quote_fees"],
            "{0:f}".format(taker2_3_details["fees"] + taker2_4_details["fees"]),
            "The quote fees returned should match the quote taker fees",
        )


class TakerRetrievalTestCase(APITestCase):
    """Class used to retrieve the taker order for a user"""

    def setUp(self):
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xf17f52151EbEF6C7334FAD080c5704D77216b732")
        )
        self.taker_user = async_to_sync(User.objects.create_user)(
            address=Address("0xf18f52151EbEF6C7334FAD080c5704D77216b732")
        )
        self.datetime = datetime.now()
        self.data = {
            "address": Web3.to_checksum_address(
                "0xf17f52151EbEF6C7334FAD080c5704D77216B732"
            ),
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 1696667304,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": Web3.to_checksum_address(
                "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"
            ),
            "quote_token": Web3.to_checksum_address(
                "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            ),
            "signature": "0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            "order_hash": "0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
        }

        self.maker = async_to_sync(Maker.objects.create)(
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

        self.taker_details = {
            "timestamp": self.datetime,
            "taker_amount": Decimal("12e17"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 18,
            "base_fees": False,
            "fees": Decimal("145e16"),
            "is_buyer": True,
        }

        self.taker = async_to_sync(Taker.objects.create)(
            taker_amount=self.taker_details["taker_amount"],
            maker=self.taker_details["maker"],
            user=self.taker_details["user"],
            timestamp=self.taker_details["timestamp"],
            block=self.taker_details["block"],
            base_fees=self.taker_details["base_fees"],
            fees=self.taker_details["fees"],
            is_buyer=self.taker_details["is_buyer"],
        )

    def test_anon_users_cannot_see_takers_orders(self):
        """The anonymous users should not be able to see taker orders"""

        response = self.client.get(reverse("api:taker"), data={"all": True})
        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The anon user shouldn't be allowed to use this endpoint",
        )

    def test_logged_in_user_can_see_his_takers(self):
        """A logged in user should see its taker orders"""

        self.client.force_authenticate(user=self.taker_user)  # type: ignore
        response = self.client.get(reverse("api:taker"), data={"all": True})

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The response should work for logged in users",
        )

        del self.taker_details["user"]
        del self.taker_details["maker"]
        self.taker_details["taker_amount"] = "{0:f}".format(
            self.taker_details["taker_amount"]
        )
        self.taker_details["fees"] = "{0:f}".format(self.taker_details["fees"])
        self.taker_details["timestamp"] = int(self.taker_details["timestamp"].timestamp())

        self.assertEqual(
            response.json()[0],
            self.taker_details,
            "The taker returned should match the one sent",
        )

    def test_retrieving_all_user_takers(self):
        """Checks retrieving all the takers orders at once work"""
        now = datetime.now()
        taker_details = {
            "taker_amount": Decimal("10e23"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 21,
            "timestamp": now,
            "base_fees": False,
            "fees": Decimal("145e16"),
            "is_buyer": True,
        }
        async_to_sync(Taker.objects.create)(
            timestamp=taker_details["timestamp"],
            taker_amount=taker_details["taker_amount"],
            maker=taker_details["maker"],
            user=taker_details["user"],
            block=taker_details["block"],
            base_fees=taker_details["base_fees"],
            fees=taker_details["fees"],
            is_buyer=taker_details["is_buyer"],
        )

        self.client.force_authenticate(user=self.taker_user)  # type: ignore
        response = self.client.get(reverse("api:taker"), data={"all": True})
        data = response.json()

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The request with several taker orders should work",
        )
        self.assertEqual(
            len(data), 2, "two taker orders should be returned on the response"
        )
        if data[0]["block"] == taker_details["block"]:
            taker2, taker1 = data[0], data[1]
        else:
            taker1, taker2 = data[0], data[1]

        del self.taker_details["user"]
        del self.taker_details["maker"]
        self.taker_details["taker_amount"] = "{0:f}".format(
            self.taker_details["taker_amount"]
        )
        self.taker_details["fees"] = "{0:f}".format(self.taker_details["fees"])
        self.taker_details["timestamp"] = int(self.taker_details["timestamp"].timestamp())

        self.assertEqual(
            taker1,
            self.taker_details,
            "The taker returned should match the one created",
        )

        del taker_details["user"]
        del taker_details["maker"]
        taker_details["taker_amount"] = "{0:f}".format(taker_details["taker_amount"])
        taker_details["fees"] = "{0:f}".format(taker_details["fees"])
        taker_details["timestamp"] = int(taker_details["timestamp"].timestamp())

        self.assertEqual(
            taker2,
            taker_details,
            "The second taker returned should match the one created",
        )

    def test_retrieving_same_pair_multiple_taker(self):
        """Checks a user can retrieve multiple orders from the same pair"""
        now = datetime.now()
        taker_details = {
            "taker_amount": Decimal("10e23"),
            "maker": self.maker,
            "user": self.taker_user,
            "block": 21,
            "timestamp": now,
            "base_fees": False,
            "fees": Decimal("145e16"),
            "is_buyer": True,
        }
        async_to_sync(Taker.objects.create)(
            timestamp=taker_details["timestamp"],
            taker_amount=taker_details["taker_amount"],
            maker=taker_details["maker"],
            user=taker_details["user"],
            block=taker_details["block"],
            base_fees=taker_details["base_fees"],
            fees=taker_details["fees"],
            is_buyer=taker_details["is_buyer"],
        )

        self.client.force_authenticate(user=self.taker_user)  # type: ignore
        response = self.client.get(
            reverse("api:taker"),
            data={
                "base_token": self.maker.base_token,
                "quote_token": self.maker.quote_token,
            },
        )
        data = response.json()

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The request with several taker orders should work",
        )
        self.assertEqual(
            len(data), 2, "two taker orders should be returned on the response"
        )
        if data[0]["block"] == taker_details["block"]:
            taker2, taker1 = data[0], data[1]
        else:
            taker1, taker2 = data[0], data[1]

        del self.taker_details["user"]
        del self.taker_details["maker"]
        self.taker_details["taker_amount"] = "{0:f}".format(
            self.taker_details["taker_amount"]
        )
        self.taker_details["fees"] = "{0:f}".format(self.taker_details["fees"])
        self.taker_details["timestamp"] = int(self.taker_details["timestamp"].timestamp())

        self.assertEqual(
            taker1,
            self.taker_details,
            "The taker returned should match the one created",
        )

        del taker_details["user"]
        del taker_details["maker"]
        taker_details["taker_amount"] = "{0:f}".format(taker_details["taker_amount"])
        taker_details["fees"] = "{0:f}".format(taker_details["fees"])
        taker_details["timestamp"] = int(taker_details["timestamp"].timestamp())
        self.assertEqual(
            taker2,
            taker_details,
            "The second taker returned should match the one created",
        )

    def test_retrieving_takers_wrong_params_fails(self):
        """Checks the takers retrieviing fails if the params are wrong"""

        self.client.force_authenticate(user=self.taker_user)  # type: ignore
        response = self.client.get(reverse("api:taker"))

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without param should fail",
        )
        self.assertEqual(response.json(), {"detail": errors.Order.BASE_QUOTE_NEEDED})

    def test_retrieve_takers_wrong_base_token(self):
        """Checks the taker retrieval fails with wrong base_token"""

        self.client.force_authenticate(user=self.taker_user)  # type: ignore
        response = self.client.get(
            reverse("api:taker"),
            data={
                "base_token": "0xz02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "quote_token": self.maker.quote_token,
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the request should fail with wrong base token",
        )
        self.assertDictEqual(
            response.json(),
            {"base_token": [errors.Address.WRONG_ADDRESS_ERROR.format("base_token")]},
        )

    def test_retrieve_takers_wrong_quote_token(self):
        """Checks the taker retrieval fails with wrong quote_token"""

        self.client.force_authenticate(user=self.taker_user)  # type: ignore
        response = self.client.get(
            reverse("api:taker"),
            data={
                "base_token": self.maker.base_token,
                "quote_token": "0xz02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the request should fail with wrong quote token",
        )
        self.assertDictEqual(
            response.json(),
            {"quote_token": [errors.Address.WRONG_ADDRESS_ERROR.format("quote_token")]},
        ) 
