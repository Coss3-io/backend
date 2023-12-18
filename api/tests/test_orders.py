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
            address=Address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
        )

    def test_creating_maker_order_works(self):
        """Checks we can create an order"""

        data = {
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
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
        }
        response = self.client.post(reverse("api:order"), data=data)
        order = Maker.objects.select_related("user").get(order_hash=data["order_hash"])
        data["address"] = Address(data["address"])
        data["bot"] = None
        self.assertDictEqual(
            data, response.json(), "The returned order should match the order sent"
        )
        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should work properly"
        )

        self.assertEqual(
            order.user.address,
            Address(data["address"]),
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
            int(order.chain_id),
            data["chain_id"],
            "The order chain_id should be reported on the order",
        )

        self.assertEqual(
            order.is_buyer,
            data["is_buyer"],
            "The order is_buyer should be reported on the order",
        )

    def test_creating_maker_twice_fails(self):
        """Checks creating the same order twice fails"""

        data = {
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
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "0",
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "chain_id": 31337,
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "signature": "0x2a418b51c1a806de0bfb7ee20c4f1f2a2065215e114dced71459487fdff799585f4e580a5fed665a8d2627c166515fdb7548b797f299256645c2f6c24383c01c1c",
            "order_hash": "0xfa429b30e2421f0bf298422705900bd922af5f5077e3eaf92cafd015c7ab97f8",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "chain_id": 31337,
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "signature": "0xbea9ea25d62d32ef4ab82b300190ce631618ab95e45f4012bc8370acc0aafa5a0987f9da4e2e378b6116c7cd40d95b859d2b1a1e19f920f7da1bc5c2c5e453571c",
            "order_hash": "0x59824d066777971a902fc0d023a399a6b90e4a2b3aead4049f21f1a17d763fa5",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "chain_id": 31337,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0xf25186b5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0xf25186B5081ff5cE73482AD761DB0eB0d25abfBF",
            "signature": "0xbea9ea25d62d32ef4ab82b300190ce631618ab95e45f4012bc8370acc0aafa5a0987f9da4e2e378b6116c7cd40d95b859d2b1a1e19f920f7da1bc5c2c5e453571c",
            "order_hash": "0x59824d066777971a902fc0d023a399a6b90e4a2b3aead4049f21f1a17d763fa5",
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
                amount="{0:f}".format(Decimal("173e16")),
                expiry=datetime.fromtimestamp(2114380800),
                price="{0:f}".format(Decimal("2e20")),
                chain_id=31337,
                base_token="0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
                quote_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                signature="0xbea9ea25d62d32ef4ab82b300190ce631618ab95e45f4012bc8370acc0aafa5a0987f9da4e2e378b6116c7cd40d95b859d2b1a1e19f920f7da1bc5c2c5e453571c",
                order_hash="0x59824d066777971a902fc0d023a399a6b90e4a2b3aead4049f21f1a17d763fa5",
                is_buyer=False,
            ),
        )

    def test_retrieve_maker_orders_anon(self):
        """checks we ca retrieve the maker orders being anon"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": datetime.fromtimestamp(2114380800),
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            chain_id=data["chain_id"],
            base_token=Address(data["base_token"]),
            quote_token=Address(data["quote_token"]),
            signature=data["signature"],
            order_hash=data["order_hash"],
            is_buyer=data["is_buyer"],
        )

        query = {
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
        }
        response = self.client.get(reverse("api:orders"), data=query)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The order retrieving should work properly",
        )
        data["bot"] = None
        data["expiry"] = int(data["expiry"].timestamp())
        data["address"] = Address(data["address"])
        data["base_token"] = Address(data["base_token"])
        data["quote_token"] = Address(data["quote_token"])
        self.assertListEqual([data], response.json())

    def test_retrieving_own_order(self):
        """Checks that no additional data is returned on own order query"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": datetime.fromtimestamp(2114380800),
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            chain_id=data["chain_id"],
            price=data["price"],
            base_token=Address(data["base_token"]),
            quote_token=Address(data["quote_token"]),
            signature=data["signature"],
            order_hash=data["order_hash"],
            is_buyer=data["is_buyer"],
        )

        query = {
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
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
        data["address"] = Address(data["address"])
        data["base_token"] = Address(data["base_token"])
        data["quote_token"] = Address(data["quote_token"])
        self.assertListEqual([data], response.json())

    def test_sending_id_field_is_not_taken_in_account(self):
        """Checks that a user sending an id along order's field is
        not taken in account for order creation
        """
        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": datetime.fromtimestamp(2114380800),
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
            "is_buyer": False,
        }

        async_to_sync(Maker.objects.create)(
            user=self.user,
            amount=data["amount"],
            expiry=data["expiry"],
            chain_id=data["chain_id"],
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
            # "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0xz0997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x0997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": "2114380800",
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x770997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            # "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "a" + "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            # "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": "2114380800a",
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            # "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "a{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            # "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0xzbbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0xbbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x44bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            # "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xZ02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0x02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xcC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            # "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x6z343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x67343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x8343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x687343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            # "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0xa1f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x9zf4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x1f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x991f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
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
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
            "is_buyer": "aFalse",
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

    def test_creating_maker_order_without_chain_id_fails(self):
        """Checks sending an order request without chain id fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            # "chain_id": 31337,
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"chain_id": [errors.General.MISSING_FIELD.format("chain_id")]},
            "The chain_id field should be required",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation without chain_id should fail",
        )

    def test_creating_maker_order_with_wrong_chain_id_fails(self):
        """Checks sending an order request with wrong chain_id fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0x4bbeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": "a",
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=data)

        self.assertDictEqual(
            response.json(),
            {"chain_id": [serializers.IntegerField.default_error_messages["invalid"]]},
            "The chain_id field should be a number",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The order creation with wrong chain_id should fail",
        )

    def test_user_creation_on_order_request(self):
        """Checks user creation works well on unregistered user order"""

        data = {
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
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
        }
        response = self.client.post(reverse("api:order"), data=data)
        User.objects.get(address=Address(data["address"]))

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The order resquest should not fail"
        )

        data["bot"] = None
        data["address"] = Address(data["address"])
        data["base_token"] = Address(data["base_token"])
        data["quote_token"] = Address(data["quote_token"])

        self.assertDictEqual(
            response.json(), data, "The returned data should match the data sent"
        )


class MakerOrderRetrievingTestCase(APITestCase):
    """Used to checks that the order retrieval works as expected"""

    def setUp(self) -> None:
        self.user_1: User = async_to_sync(User.objects.create_user)(
            address=Address(Address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8"))
        )

        self.user_2: User = async_to_sync(User.objects.create_user)(
            address=Address(Address("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"))
        )

        self.user_3: User = async_to_sync(User.objects.create_user)(
            address=Address(Address("0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"))
        )

        self.order_1_1 = {
            "address": self.user_1.address,
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "chain_id": 31337,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": Address("0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"),
            "quote_token": Address("0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
            "signature": "0x68343d2c50955f78107a1c17d3607ef839738d5a6d627f77f869c3f2cff1ec2b5ff6507cb20ec34434c5f1eebd9e4f21ef492deff30c0e916f61c352e6b24c031c",
            "order_hash": "0x91f4f7ac26bc9ddeafe32ec4b83dd8e0eeea87285ee818d1427c7145bf3e7c56",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None,
        }

        self.order_1_2 = {
            "address": self.user_1.address,
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 1696667304,
            "chain_id": 31337,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": Address("0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"),
            "quote_token": Address("0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
            "signature": "0x3b5de7837c06364ed56c3ddf6476e7b91e28cac6d290abf3bcb04f7b090e6fe2667d3b1d88abc1e4357a4eda330be501ac4dafd08cced0a7572214212ef816721c",
            "order_hash": "0x3716bca7ee25b52ad4f6dcb2592979f07acd2b9748a00931b496d25c48220f1b",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None,
        }

        self.order_1_3 = {
            "address": self.user_1.address,
            "amount": "{0:f}".format(Decimal("171e16")),
            "chain_id": 31337,
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("21e19")),
            "base_token": Address("0x3Aa5f43c7C4e2C5671A96439F1fbFfe1d58929Cb"),
            "quote_token": Address("0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
            "signature": "0x8c07df9323aee794c3eaedf46c6f24354d448f2e3d7f82941e3e5b41957e1f98371c985134ae3345bb216f688ba7852ed05de32e4b91faa6c22652283a5b5a001b",
            "order_hash": "0xdbdaa927a4cb7453b9cd2b2adf64502d54d7bb1b84a8f529291f457bab0c503d",
            "is_buyer": False,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None,
        }

        self.order_2_1 = {
            "address": self.user_2.address,
            "amount": "{0:f}".format(Decimal("111e16")),
            "chain_id": 31337,
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("24e19")),
            "base_token": Address("0x3AA5f43c7c4e2C5671A96439F1fbFfe1d58929Cb"),
            "quote_token": Address("0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
            "signature": "0x6911a61f42ca52ed5d9ade2e8aea795bb87fadaabd56a3f88e01f6cb0edb3abf1a14771487902e2d405816d4202dc9d39fdb88df2e79dfd85f6f12432ddaf1511c",
            "order_hash": "0x0db81ac8066a45b3a5e5451aee859d1edb74d1f5a784adaa5b701462ece50166",
            "is_buyer": True,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None,
        }

        self.order_2_2 = {
            "address": self.user_2.address,
            "amount": "{0:f}".format(Decimal("141e16")),
            "chain_id": 31337,
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("25e19")),
            "base_token": Address("0x3AA5f43c7c4e2C5671A96439F1fbFfe1d58929Cb"),
            "quote_token": Address("0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
            "signature": "0xd9ba072ccfbc1705807d7bd20a5450e90c3b15f19b671440a8d36eeeebdc79747b7d54472bc324e24c17d8acc4ad91ac28943ea85452b17c7cfd62777806e6291b",
            "order_hash": "0xf5b6fcc43ab8d8f63b19cec2fbb9cd4902662c2eb0431da96d92fdcf9b93a50d",
            "is_buyer": True,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None,
        }

        self.order_2_3 = {
            "address": self.user_2.address,
            "amount": "{0:f}".format(Decimal("182e16")),
            "chain_id": 31337,
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("27e19")),
            "base_token": Address("0x3AA5f43c7c4e2C5671A96439F1fbFfe1d58929Cb"),
            "quote_token": Address("0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
            "signature": "0x9698fde6e6fce9beaf65a91de15206b826d12b8fde0dd2e3821b5d7ab08c83f93068023cc234006de517a242a51947ecbd716cf756bddf94109385828ea4ed0e1b",
            "order_hash": "0x7d9c352d212ae33744010ea6798b2af8760e6d50a270cce78e853df44989689e",
            "is_buyer": True,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None,
        }

        self.order_2_4 = {
            "address": self.user_2.address,
            "amount": "{0:f}".format(Decimal("189e16")),
            "chain_id": 31337,
            "expiry": 2114380801,
            "price": "{0:f}".format(Decimal("29e19")),
            "base_token": Address("0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"),
            "quote_token": Address("0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
            "signature": "0x6c402ddc62d05ebab06febed2e12d69966a1a0c1bd1be9debd79d0e097459a6e4fe506baa8fde3ba56cce65f94a214c492573de86774f6fd1b07e101f35647cd1b",
            "order_hash": "0x33273c10d8b6c33afe37ba26a1018957dee8b28b669df324e96fc23fb37ee95d",
            "is_buyer": True,
            "filled": "0",
            "base_fees": "0",
            "quote_fees": "0",
            "status": "OPEN",
            "bot": None,
        }

        self.pair_1 = {
            "base_token": "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520",
            "quote_token": "0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
        }
        self.pair_2 = {
            "base_token": "0x3AA5f43c7c4e2C5671A96439f1fbFfe1d58929Cb",
            "quote_token": "0xC02AAA39b223FE8D0A0E5C4F27eAD9083C756Cc2",
            "chain_id": 31337,
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
                chain_id=data["chain_id"],
                price=data["price"],
                base_token=Address(data["base_token"]),
                quote_token=Address(data["quote_token"]),
                signature=data["signature"],
                order_hash=data["order_hash"],
                is_buyer=data["is_buyer"],
            )

    def test_retrieving_auth_no_orders_works(self):
        """Checks the empty order retrieval works"""

        self.client.force_authenticate(user=self.user_3)  # type: ignore
        response = self.client.get(
            reverse("api:order"), data={"all": True, "chain_id": 31337}
        )

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

        response = self.client.get(
            reverse("api:order"), data={"all": True, "chain_id": 31337}
        )

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

        response = self.client.get(
            reverse("api:order"), data={"all": True, "chaind_id": 31337}
        )

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
            response.json(),
            {
                "chain_id": errors.General.MISSING_FIELD,
            },
        )

    def test_getting_own_orders_without_base_token(self):
        """Checks getting own orders without base_token params fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={"quote_token": self.pair_2["quote_token"], "chain_id": 31337},
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
        """Checks getting own orders without quote_token params fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={"base_token": self.pair_2["base_token"], "chain_id": 31337},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without quote_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(), {"detail": "base_token and quote_token params are needed"}
        )

    def test_getting_own_orders_without_chain_id(self):
        """Checks getting own orders without chain_id params fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={"base_token": self.pair_2["base_token"]},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without chain_id parameter should fail",
        )

        self.assertDictEqual(
            response.json(), {"chain_id": errors.General.MISSING_FIELD}
        )

    def test_getting_own_orders_wrong_base_token(self):
        """Checks getting own orders with wrong base token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={
                "base_token": "0xZ02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "quote_token": self.pair_2["quote_token"],
                "chain_id": 31337,
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
                "chain_id": 31337,
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

    def test_getting_own_orders_wrong_chain_id(self):
        """Checks getting own orders with wrong chain_id fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={
                "quote_token": "0xZ02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "base_token": self.pair_2["quote_token"],
                "chain_id": "a31337",
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with wrong chain_id parameter should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"chain_id": serializers.IntegerField.default_error_messages["invalid"]},
        )

    def test_getting_own_orders_short_base_token(self):
        """Checks getting own orders with short base token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:order"),
            data={
                "base_token": "0x02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "quote_token": self.pair_2["quote_token"],
                "chain_id": 31337,
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
                "chain_id": 31337,
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
                "chain_id": 31337,
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
                "chain_id": 31337,
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

    def test_getting_general_orders_without_chain_id(self):
        """Checks getting general orders without chain_id params fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:orders"),
            data={
                "base_token": self.pair_2["base_token"],
                "quote_token": self.pair_2["quote_token"],
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request without quote_token parameter should fail",
        )

        self.assertDictEqual(
            response.json(), {"chain_id": errors.General.MISSING_FIELD}
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

    def test_getting_general_orders_wrong_chain_id(self):
        """Checks getting general orders with wrong quote token fails"""

        self.client.force_authenticate(user=self.user_2)  # type: ignore
        response = self.client.get(
            reverse("api:orders"),
            data={
                "quote_token": self.pair_2["base_token"],
                "base_token": self.pair_2["quote_token"],
                "chain_id": "a",
            },
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with wrong chain_id should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"chain_id": serializers.IntegerField.default_error_messages["invalid"]},
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
            "address": Address("0xf17f52151EbEF6C7334FAD080c5704D77216B732"),
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 1696667304,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": Address("0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"),
            "quote_token": Address("0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
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
            base_token=Address(self.data["base_token"]),
            quote_token=Address(self.data["quote_token"]),
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
            "address": Address("0xf17f52151Ebef6C7334FAD080c5704D77216b732"),
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": Address("0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"),
            "quote_token": Address("0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
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
            base_token=Address(self.data["base_token"]),
            quote_token=Address(self.data["quote_token"]),
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
            "address": Address("0xf17f52151EbEF6C7334FAD080c5704D77216B732"),
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 1696667304,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": Address("0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"),
            "quote_token": Address("0xC02AAA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
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
            base_token=Address(self.data["base_token"]),
            quote_token=Address(self.data["quote_token"]),
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
        self.taker_details["timestamp"] = int(
            self.taker_details["timestamp"].timestamp()
        )

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
        self.taker_details["timestamp"] = int(
            self.taker_details["timestamp"].timestamp()
        )

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
        self.taker_details["timestamp"] = int(
            self.taker_details["timestamp"].timestamp()
        )

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
