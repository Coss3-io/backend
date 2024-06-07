from decimal import Decimal
from time import time
from asgiref.sync import async_to_sync
from django.urls import reverse
from django.db.models import F
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from rest_framework.test import APITestCase
from rest_framework.serializers import DecimalField, BooleanField, IntegerField
from rest_framework.exceptions import NotAuthenticated
from web3 import Web3
from api.models import User
from api.models.orders import Maker, Bot
from api.models.types import Address
import api.errors as errors
from api.utils import encode_order


class ReplacementOrdersCreationTestCase(APITestCase):
    """Class used for the testing of the bot creation"""

    def test_create_a_bot(self):
        """Checks the bot creation works well"""
        timestamp = int(time())
        data = {
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

        response = self.client.post(reverse("api:bot"), data=data)
        base_token_amount = Decimal("0")
        quote_token_amount = Decimal("0")

        User.objects.get(address=Address(data.get("address", "")))
        orders = self.client.get(
            reverse("api:orders"),
            data={
                "base_token": data.get("base_token"),
                "quote_token": data.get("quote_token"),
                "chain_id": data.get("chain_id"),
            },
        ).json()

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The bot creation should work properly"
        )

        prices = [
            str(int(price))
            for price in range(
                int(data.get("lower_bound", 0)),
                int(data.get("upper_bound", 0)) + int(data.get("step", 0)),
                int(data.get("step", 0)),
            )
        ]

        for order in orders:
            self.assertEqual(
                order["chain_id"],
                data.get("chain_id", ""),
                "The chain_id on the returned order should match the bot creator chain_id",
            )

            self.assertEqual(
                order["address"],
                Address(data.get("address", "")),
                "The address on the returned order should match the bot creator address",
            )

            self.assertEqual(
                order.get("expiry"),
                data.get("expiry"),
                "The expiry field should be part of the orders",
            )

            self.assertEqual(
                order.get("signature"),
                data.get("signature"),
                "The signature of the replacement orders should be reported into the orders",
            )

            if Decimal(order.get("price")) <= Decimal(data.get("price", 0)):
                self.assertEqual(
                    order.get("is_buyer"),
                    True,
                    "If the price of the order is below the thresold price, the order should be a buyer",
                )
                quote_token_amount += (
                    Decimal(order.get("amount"))
                    * Decimal(order.get("price"))
                    / Decimal("1e18")
                ).quantize(Decimal("1."))
            else:
                self.assertEqual(
                    order.get("is_buyer"),
                    False,
                    "If the price is strictly above the threesold price, the order should be a sell",
                )
                base_token_amount += Decimal(order.get("amount"))

            self.assertEqual(
                order["bot"].get("step"),
                data.get("step"),
                "The step field should be reported into the orders created",
            )

            self.assertEqual(
                order["bot"].get("maker_fees"),
                data.get("maker_fees"),
                "The maker_fees field should be reported into the orders created",
            )

            self.assertIsNotNone(
                prices.index(order.get("price")),
                "The price of the order should be in the prices list",
            )
            prices.pop(prices.index(order.get("price")))

            self.assertEqual(
                order["bot"].get("lower_bound"),
                data.get("lower_bound"),
                "The orders lower bound should match the bot lower bound",
            )
            self.assertEqual(
                order.get("amount"),
                data.get("amount"),
                "The orders amount should match the bot amount",
            )
            self.assertEqual(
                order.get("base_token"),
                Address(data.get("base_token", "")),
                "The orders base_token should match the bot base_token",
            )
            self.assertEqual(
                order.get("quote_token"),
                Address(data.get("quote_token", "")),
                "The orders quote_token should match the bot quote_token",
            )

        self.assertListEqual(
            prices, [], "All the prices of the range should be into the orders"
        )

        self.assertEqual(
            response.json()["bot_hash"],
            "0x53fa53d0d1ca0e7263da21ed4379578ed0964b6de73f73b5a155ad013b66194c",
            "The bot hash should match the one computed on chain",
        )

        data["address"] = Address(data.get("address", ""))
        data["base_token"] = Address(data.get("base_token", ""))
        data["quote_token"] = Address(data.get("quote_token", ""))

        bot_data = response.json()
        bot_timestamp = bot_data["timestamp"]
        del bot_data["timestamp"]
        data["is_buyer"] = int(not data["is_buyer"])
        data.update(
            {
                "bot_hash": str(
                    Web3.to_hex(
                        Web3.keccak(encode_order(data | {"replace_order": True}))
                    )
                ),
                "base_token_amount": "{0:f}".format(base_token_amount),
                "quote_token_amount": "{0:f}".format(quote_token_amount),
                "fees_earned": "0",
            }
        )
        del data["is_buyer"]
        self.assertDictEqual(
            bot_data,
            data,
            "The returned bot data should hold all the bot informations",
        )

        self.assertAlmostEqual(
            timestamp, bot_timestamp, delta=3, msg="The two timestamps should be equal"
        )

    def test_create_a_bot_specific_values(self):
        """Checks the bot computes the right base and quote token amounts"""
        timestamp = int(time())
        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x96d0cdda397323b958bb4bf0b990325a499439b51039a188efd4f84c0e7eadd21fe7f58e45e67d9d6710103a7851367c092783b60f74bbad5dcee65105ae91f51c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("66e18")),
            "price": "{0:f}".format(Decimal("15000e18")),
            "maker_fees": "{0:f}".format(Decimal("440")),
            "upper_bound": "{0:f}".format(Decimal("21450e18")),
            "lower_bound": "{0:f}".format(Decimal("4050e18")),
            "amount": "{0:f}".format(Decimal("78e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)
        data = response.json()
        base_token_amount = "{0:f}".format(Decimal("7644e18"))
        quote_token_amount = "{0:f}".format(Decimal("122941260e18"))

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should succeed"
        )
        self.assertEqual(
            base_token_amount,
            data["base_token_amount"],
            "The computed base token amount needed should be identical",
        )
        self.assertEqual(
            quote_token_amount,
            data["quote_token_amount"],
            "The computed quote token amount needed should be identical",
        )

    def test_create_a_bot_specific_values_2(self):
        """Test to create a bot with not round values to check the app behaviour"""

        timestamp = int(time())
        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 1337,
            "expiry": 2114380800,
            "signature": "0xd8778514349cea777e47362782c3b4724576bddc3aaa9997c32b641e3613f7a245723166eca951cd4b706d42931be170a7e416c7e7eae9ad6eaef8820d29cbc71c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("3e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)
        base_token_amount = Decimal("0")
        quote_token_amount = Decimal("0")

        User.objects.get(address=Address(data.get("address", "")))
        orders = self.client.get(
            reverse("api:orders"),
            data={
                "base_token": data.get("base_token"),
                "quote_token": data.get("quote_token"),
                "chain_id": data.get("chain_id"),
            },
        ).json()

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The bot creation should work properly"
        )

        prices = [
            str(int(price))
            for price in range(
                int(data.get("lower_bound", 0)),
                int(data.get("upper_bound", 0)) + 1,
                int(data.get("step", 0)),
            )
        ]

        for order in orders:
            self.assertEqual(
                order["chain_id"],
                data.get("chain_id", ""),
                "The chain_id on the returned order should match the bot creator chain_id",
            )

            self.assertEqual(
                order["address"],
                Address(data.get("address", "")),
                "The address on the returned order should match the bot creator address",
            )

            self.assertEqual(
                order.get("expiry"),
                data.get("expiry"),
                "The expiry field should be part of the orders",
            )

            self.assertEqual(
                order.get("signature"),
                data.get("signature"),
                "The signature of the replacement orders should be reported into the orders",
            )

            if Decimal(order.get("price")) <= Decimal(data.get("price", 0)):
                self.assertEqual(
                    order.get("is_buyer"),
                    True,
                    "If the price of the order is below the thresold price, the order should be a buyer",
                )
                quote_token_amount += (
                    Decimal(order.get("amount"))
                    * Decimal(order.get("price"))
                    / Decimal("1e18")
                ).quantize(Decimal("1."))
            else:
                self.assertEqual(
                    order.get("is_buyer"),
                    False,
                    "If the price is strictly above the threesold price, the order should be a sell",
                )
                base_token_amount += Decimal(order.get("amount"))

            self.assertEqual(
                order["bot"].get("step"),
                data.get("step"),
                "The step field should be reported into the orders created",
            )

            self.assertEqual(
                order["bot"].get("maker_fees"),
                data.get("maker_fees"),
                "The maker_fees field should be reported into the orders created",
            )

            self.assertIsNotNone(
                prices.index(order.get("price")),
                "The price of the order should be in the prices list",
            )
            prices.pop(prices.index(order.get("price")))

            self.assertEqual(
                order["bot"].get("lower_bound"),
                data.get("lower_bound"),
                "The orders lower bound should match the bot lower bound",
            )
            self.assertEqual(
                order.get("amount"),
                data.get("amount"),
                "The orders amount should match the bot amount",
            )
            self.assertEqual(
                order.get("base_token"),
                Address(data.get("base_token", "")),
                "The orders base_token should match the bot base_token",
            )
            self.assertEqual(
                order.get("quote_token"),
                Address(data.get("quote_token", "")),
                "The orders quote_token should match the bot quote_token",
            )

        self.assertListEqual(
            prices, [], "All the prices of the range should be into the orders"
        )

        self.assertEqual(
            response.json()["bot_hash"],
            "0x9f9e0282f709b1c57775b34cb9460af387accfc90d3d9fbbcd181a73118c6bb1",
            "The bot hash should match the one computed on chain",
        )

        data["address"] = Address(data.get("address", ""))
        data["base_token"] = Address(data.get("base_token", ""))
        data["quote_token"] = Address(data.get("quote_token", ""))

        bot_data = response.json()
        bot_timestamp = bot_data["timestamp"]
        del bot_data["timestamp"]
        data["is_buyer"] = int(not data["is_buyer"])
        data.update(
            {
                "bot_hash": str(
                    Web3.to_hex(
                        Web3.keccak(encode_order(data | {"replace_order": True}))
                    )
                ),
                "base_token_amount": "{0:f}".format(base_token_amount),
                "quote_token_amount": "{0:f}".format(quote_token_amount),
                "fees_earned": "0",
            }
        )
        del data["is_buyer"]
        self.assertDictEqual(
            bot_data,
            data,
            "The returned bot data should hold all the bot informations",
        )

        self.assertAlmostEqual(
            timestamp, bot_timestamp, delta=3, msg="The two timestamps should be equal"
        )

    def test_sending_a_date_on_bot_creation_is_ignored(self):
        """Checks that if a user send a date on bot creation the date is not taken in account"""
        timestamp = int(time())
        data = {
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
            "timestamp": 200000,
        }

        response = self.client.post(reverse("api:bot"), data=data).json()

        self.assertAlmostEqual(
            timestamp,
            response["timestamp"],
            delta=1,
            msg="The timestamp sent by the user should be ignored on bot creation",
        )

    def test_creating_twice_the_same_bot_fails(self):
        """A user should not be able to create the same bot twice"""

        data = {
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

        self.client.post(reverse("api:bot"), data=data)
        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "Creating a bot twice should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Order.BOT_EXISTING_ORDER]},
            "Creating a bot with already existing orders should fail",
        )

    def test_creating_bot_with_0_step_fails(self):
        """Creating a bot with a 0 step should not be allowed"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "0",
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a 0 step field should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"step": [errors.Decimal.ZERO_DECIMAL_ERROR.format("step")]},
            "the error returned should be about the 0 step field",
        )

    def test_creating_bot_with_0_amount_fails(self):
        """Creating a bot with a 0 amount should not be allowed"""

        data = {
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
            "amount": "0",
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a 0 amount field should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"amount": [errors.Decimal.ZERO_DECIMAL_ERROR.format("amount")]},
            "the error returned should be about the 0 amount field",
        )

    def test_creating_bot_with_0_maker_fees_fails(self):
        """Creating a bot with a 0 maker_fees should not be allowed"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "0",
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a 0 price field should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"maker_fees": [errors.Decimal.ZERO_DECIMAL_ERROR.format("maker_fees")]},
            "the error returned should be about the 0 amount field",
        )

    def test_creating_a_bot_same_base_and_quote_fails(self):
        """Checks that creating a bot with the same base and the same quote fails"""

        data = {
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
            "quote_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
        }

        response = self.client.post(reverse("api:bot"), data=data)
        self.assertDictEqual(
            response.json(),
            {"error": [errors.Order.SAME_BASE_QUOTE_ERROR]},
            "The bot creation should fail with same base and same quote token",
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the response status code should be 400",
        )

    def test_creating_a_bot_with_price_gt_upper_bound(self):
        """The creation of a bot with price gt upper bound should fail"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("16e17")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Order.PRICE_GT_UPPER_BOUND]},
            "A bot with price greater than upper bound should not be created",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request should fail when price is greater than upper bound",
        )

    def test_creating_a_bot_with_lower_bound_gt_price(self):
        """The creation of a bot with price gt upper bound should fail"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("11e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Order.LOWER_BOUND_GT_PRICE]},
            "A bot with lower bound greater than price should not be created",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request should fail when lower bound is greater than price",
        )

    def test_creating_a_bot_with_lower_bound_gte_upper_bound_fails(self):
        """Checks creating a bot with lower bound greater or equal to upper bound fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("16e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Order.LOWER_BOUND_GTE_UPPER_BOUND]},
            "A bot with lower bound greater than upper_bound should not be created",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request should fail when lower_bound is greater than upper_bound",
        )

    def test_bot_orders_and_regular_orders(self):
        """Checks with bot orders and regular order we can get all of them at once"""

        data = {
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

        maker_data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
            "signature": "0x5e5c78f1462f8ac5c05a68b87f6bbcdc23e0cedb2f87c40780d63eb30a79fdc261fd045ad597bf61ba3cd91804e4ce1fb4f5e90a17838fa3623cdfa35815d6831b",
            "order_hash": "0xcf6fc7283e9413379175d181adddd50251f33a3b3687c9cd07ad65bc18ac12b1",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=maker_data)
        self.client.post(reverse("api:bot"), data=data)

        orders = self.client.get(
            reverse("api:orders"),
            data={
                "base_token": data.get("base_token"),
                "quote_token": data.get("quote_token"),
                "chain_id": 31337,
            },
        ).json()

        prices = [
            str(int(price))
            for price in range(
                int(data.get("lower_bound", 0)),
                int(data.get("upper_bound", 0)) + int(data.get("step", 0)),
                int(data.get("step", 0)),
            )
        ]

        for order in list(orders):
            if order.get("price") in prices:
                orders.remove(order)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The regular maker order creation should work",
        )

        self.assertEqual(
            len(orders), 1, "Only the maker order should be left on the orders array"
        )

        self.assertEqual(
            orders[0].get("order_hash"),
            maker_data["order_hash"],
            "The last order should be our maker order",
        )

    def test_create_a_bot_without_address_fails(self):
        """Checks creating a bot without address fails"""

        data = {
            # "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without address should fail",
        )

        self.assertEqual(
            response.json(),
            {"address": [errors.General.MISSING_FIELD.format("address")]},
        )

    def test_create_a_bot_with_short_address_fails(self):
        """Checks creating a bot with a short address fails"""

        data = {
            "address": "0x0997970C51812dc3A010C7d01b50e0d17dc79C8",
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with short address should fail",
        )

        self.assertEqual(
            response.json(),
            {"address": [errors.Address.SHORT_ADDRESS_ERROR.format("")]},
        )

    def test_create_a_bot_with_a_long_address_fails(self):
        """Checks creating a bot with a long address fails"""

        data = {
            "address": "0x470997970C51812dc3A010C7d01b50e0d17dc79C8",
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with long address should fail",
        )

        self.assertEqual(
            response.json(),
            {"address": [errors.Address.LONG_ADDRESS_ERROR.format("")]},
        )

    def test_create_a_bot_with_wrong_address_fails(self):
        """Checks creating a bot with wrong address fails"""

        data = {
            "address": "0xz0997970C51812dc3A010C7d01b50e0d17dc79C8",
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong address should fail",
        )

        self.assertEqual(
            response.json(),
            {"address": [errors.Address.WRONG_ADDRESS_ERROR.format("")]},
        )

    def test_create_a_bot_without_expiry_fails(self):
        """Checks creating a bot without expiry fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            # "expiry": 2114380800,
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without expiry should fail",
        )

        self.assertEqual(
            response.json(),
            {"expiry": [errors.General.MISSING_FIELD.format("expiry")]},
        )

    def test_create_a_bot_with_wrong_expiry_fails(self):
        """Checks creating a bot with wrong expiry fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": "z2114380800",
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong expiry should fail",
        )

        self.assertEqual(
            response.json(),
            {"expiry": [errors.Decimal.WRONG_DECIMAL_ERROR.format("expiry")]},
        )

    def test_create_a_bot_without_is_buyer_fails(self):
        """Checks creating a bot without is_buyer fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            # "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without is_buyer should fail",
        )

        self.assertEqual(
            response.json(),
            {"is_buyer": [errors.General.MISSING_FIELD.format("is_buyer")]},
        )

    def test_create_a_bot_with_wrong_is_buyer_fails(self):
        """Checks creating a bot with wrong is_buyer fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": "aFalse",
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong is_buyer should fail",
        )

        self.assertEqual(
            response.json(),
            {"is_buyer": [BooleanField.default_error_messages["invalid"]]},
        )

    def test_create_a_bot_without_signature_fails(self):
        """Checks creating a bot without signature fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            # "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without signature should fail",
        )

        self.assertEqual(
            response.json(),
            {"signature": [errors.General.MISSING_FIELD.format("signature")]},
        )

    def test_create_a_bot_with_short_signature_fails(self):
        """Checks creating a bot with_short signature fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x04b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with short signature should fail",
        )

        self.assertEqual(
            response.json(),
            {"signature": [errors.Signature.SHORT_SIGNATURE_ERROR]},
        )

    def test_create_a_bot_with_long_signature_fails(self):
        """Checks creating a bot with long signature fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4bb8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with long signature should fail",
        )

        self.assertEqual(
            response.json(),
            {"signature": [errors.Signature.LONG_SIGNATURE_ERROR]},
        )

    def test_create_a_bot_with_wrong_signature_fails(self):
        """Checks creating a bot with wrong signature fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0z4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong signature should fail",
        )

        self.assertEqual(
            response.json(),
            {"signature": [errors.Signature.WRONG_SIGNATURE_ERROR]},
        )

    def test_create_a_bot_with_mismatch_signature_fails(self):
        """Checks creating a bot with a mismatch signature fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0a4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with a mismatch signature should fail",
        )

        self.assertEqual(
            response.json(),
            {"error": [errors.Signature.SIGNATURE_MISMATCH_ERROR]},
        )

    def test_create_a_bot_without_step_fails(self):
        """Checks creating a bot without step fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            # "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without step should fail",
        )

        self.assertEqual(
            response.json(),
            {"step": [errors.General.MISSING_FIELD.format("step")]},
        )

    def test_create_a_bot_with_wrong_step_fails(self):
        """Checks creating a bot with wrong step fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "a{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong step should fail",
        )

        self.assertEqual(
            response.json(),
            {"step": [DecimalField.default_error_messages["invalid"]]},
        )

    def test_create_a_bot_without_price_fails(self):
        """Checks creating a bot without price fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            # "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without price should fail",
        )

        self.assertEqual(
            response.json(),
            {"price": [errors.General.MISSING_FIELD.format("price")]},
        )

    def test_create_a_bot_with_wrong_price_fails(self):
        """Checks creating a bot with wrong price fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "a{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong price should fail",
        )

        self.assertEqual(
            response.json(),
            {"price": [DecimalField.default_error_messages["invalid"]]},
        )

    def test_create_a_bot_without_maker_fees_fails(self):
        """Checks creating a bot without maker_fees fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            # "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without maker_fees should fail",
        )

        self.assertEqual(
            response.json(),
            {"maker_fees": [errors.General.MISSING_FIELD.format("maker_fees")]},
        )

    def test_create_a_bot_with_wrong_maker_fees_fails(self):
        """Checks creating a bot without price fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "a{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong maker_fees should fail",
        )

        self.assertEqual(
            response.json(),
            {"maker_fees": [DecimalField.default_error_messages["invalid"]]},
        )

    def test_create_a_bot_without_upper_bound_fails(self):
        """Checks creating a bot without upper_bound fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            # "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without upper_bound should fail",
        )

        self.assertEqual(
            response.json(),
            {"upper_bound": [errors.General.MISSING_FIELD.format("upper_bound")]},
        )

    def test_create_a_bot_with_wrong_upper_bound_fails(self):
        """Checks creating a bot with wrong upper_bound fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "a{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong upper_bound should fail",
        )

        self.assertEqual(
            response.json(),
            {"upper_bound": [DecimalField.default_error_messages["invalid"]]},
        )

    def test_create_a_bot_without_lower_bound_fails(self):
        """Checks creating a bot without lower_bound fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            # "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without lower_bound should fail",
        )

        self.assertEqual(
            response.json(),
            {"lower_bound": [errors.General.MISSING_FIELD.format("lower_bound")]},
        )

    def test_create_a_bot_with_wrong_lower_bound_fails(self):
        """Checks creating a bot with wrong lower_bound fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": 31337,
            "expiry": 2114380800,
            "signature": "0x0e4b8968194fe008b2766a7c2920dc5784cc23f2ec785fb605c51d48f18295121ee57d4f0c33250554b2ac1980ea4c9067ef1680b08195a768b2a1239cff6b851b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "a{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong lower_bound should fail",
        )

        self.assertEqual(
            response.json(),
            {"lower_bound": [DecimalField.default_error_messages["invalid"]]},
        )

    def test_create_a_bot_without_amount_fails(self):
        """Checks creating a bot without amount fails"""

        data = {
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
            # "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without amount should fail",
        )

        self.assertEqual(
            response.json(),
            {"amount": [errors.General.MISSING_FIELD.format("amount")]},
        )

    def test_create_a_bot_with_wrong_amount_fails(self):
        """Checks creating a bot with wrong amount fails"""

        data = {
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
            "amount": "a{0:f}".format(Decimal("2e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong amount should fail",
        )

        self.assertEqual(
            response.json(),
            {"amount": [DecimalField.default_error_messages["invalid"]]},
        )

    def test_create_a_bot_without_base_token_fails(self):
        """Checks creating a bot without base token fails"""

        data = {
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
            # "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without base_token should fail",
        )

        self.assertEqual(
            response.json(),
            {"base_token": [errors.General.MISSING_FIELD.format("base_token")]},
        )

    def test_create_a_bot_with_wrong_base_token_fails(self):
        """Checks creating a bot with wrong base token fails"""

        data = {
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
            "base_token": "0xz25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong base_token should fail",
        )

        self.assertEqual(
            response.json(),
            {"base_token": [errors.Address.WRONG_ADDRESS_ERROR.format("base_token")]},
        )

    def test_create_a_bot_with_short_base_token_fails(self):
        """Checks creating a bot with short base token fails"""

        data = {
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
            "base_token": "0x25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with short base_token should fail",
        )

        self.assertEqual(
            response.json(),
            {"base_token": [errors.Address.SHORT_ADDRESS_ERROR.format("base_token")]},
        )

    def test_create_a_bot_with_long_base_token_fails(self):
        """Checks creating a bot with long base token fails"""

        data = {
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
            "base_token": "0xFa25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with long base_token should fail",
        )

        self.assertEqual(
            response.json(),
            {"base_token": [errors.Address.LONG_ADDRESS_ERROR.format("base_token")]},
        )

    def test_create_a_bot_without_quote_token_fails(self):
        """Checks creating a bot without quote token fails"""

        data = {
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
            # "quote_token": "0x345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without quote_token should fail",
        )

        self.assertEqual(
            response.json(),
            {"quote_token": [errors.General.MISSING_FIELD.format("quote_token")]},
        )

    def test_create_a_bot_with_wrong_quote_token_fails(self):
        """Checks creating a bot with wrong quote token fails"""

        data = {
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
            "quote_token": "0xz45CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong quote_token should fail",
        )

        self.assertEqual(
            response.json(),
            {"quote_token": [errors.Address.WRONG_ADDRESS_ERROR.format("quote_token")]},
        )

    def test_create_a_bot_with_short_quote_token_fails(self):
        """Checks creating a bot with short quote token fails"""

        data = {
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
            "quote_token": "0x45CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with short quote_token should fail",
        )

        self.assertEqual(
            response.json(),
            {"quote_token": [errors.Address.SHORT_ADDRESS_ERROR.format("quote_token")]},
        )

    def test_create_a_bot_with_long_quote_token_fails(self):
        """Checks creating a bot with long quote token fails"""

        data = {
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
            "quote_token": "0x3345CA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with long quote_token should fail",
        )

        self.assertEqual(
            response.json(),
            {"quote_token": [errors.Address.LONG_ADDRESS_ERROR.format("quote_token")]},
        )

    def test_create_a_bot_without_chain_id_fails(self):
        """Checks creating a bot without chain id fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            # "chain_id": 31337,
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation without chain_id should fail",
        )

        self.assertEqual(
            response.json(),
            {"chain_id": [errors.General.MISSING_FIELD]},
        )

    def test_create_a_bot_with_wrong_chain_id_fails(self):
        """Checks creating a bot with wrong chain_id fails"""

        data = {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "chain_id": "a31337",
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

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The bot creation with wrong chain_id should fail",
        )

        self.assertEqual(
            response.json(),
            {"chain_id": [IntegerField.default_error_messages["invalid"]]},
        )


class BotRetrievalTestCase(APITestCase):
    """Class used to test the retrieval of the users bots"""

    def setUp(self):
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
        )
        self.timestamp = int(time())
        self.data = {
            "address": Address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8"),
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
            "base_token": Address("0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF"),
            "quote_token": Address("0x345CA3e014Aaf5dcA488057592ee47305D9B3e10"),
        }
        self.client.post(reverse("api:bot"), data=self.data)

    def test_retrieving_user_bots_works(self):
        """Checks retrieving the bots of a user works"""

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(
            reverse("api:bot"), {"chain_id": self.data["chain_id"]}
        )
        data = response.json()
        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The bot retrieval request should be successfull",
        )

        del self.data["signature"]

        self.data["base_token"] = Address(self.data.get("base_token", ""))
        self.data["quote_token"] = Address(self.data.get("quote_token", ""))
        self.data["address"] = Address(self.data.get("address", ""))

        bot_timestamp = data[0]["timestamp"]
        del data[0]["timestamp"]
        self.data["is_buyer"] = int(not self.data["is_buyer"])

        self.data.update(
            {
                "bot_hash": str(
                    Web3.to_hex(
                        Web3.keccak(encode_order(self.data | {"replace_order": True}))
                    )
                ),
                "base_token_amount": "{0:f}".format(Decimal("10e18")),
                "quote_token_amount": "{0:f}".format(Decimal("9e18")),
                "fees_earned": "0",
            }
        )
        del self.data["is_buyer"]

        self.assertEqual(len(data), 1, "only one bot should be available for the user")
        self.assertDictEqual(
            data[0], self.data, "The returned data shold contain the bot informations"
        )

        self.assertAlmostEqual(
            self.timestamp,
            bot_timestamp,
            delta=1,
            msg="The returned bot timestamp should match the creation timestamp",
        )

    def test_retrieving_bots_anon_fails(self):
        """Checks that a non authenticated user cannot get his bots list"""

        response = self.client.get(
            reverse("api:bot"), {"chain_id": self.data["chain_id"]}
        )

        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The non auth user should not be able to view bots ",
        )

        self.assertDictEqual(
            response.json(), {"detail": NotAuthenticated.default_detail}
        )

    def test_retrieving_bots_without_chain_id_fails(self):
        """Checks that not sending the chain id fails the request"""

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:bot"))

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "Chain_id is required to get your bots list",
        )

        self.assertDictEqual(
            response.json(), {"chain_id": errors.General.MISSING_FIELD}
        )

    def test_retrieving_user_bots_with_consummed_orders_works(self):
        """
        Checks a bot with some orders being consummed
        are returned with the right balances
        """
        bot = Bot.objects.get(user=self.user)
        buyer: Maker = Maker.objects.filter(
            bot=bot,
            is_buyer=True,
            base_token=Address(self.data.get("base_token", "")),
            quote_token=Address(self.data.get("quote_token", "")),
        ).first()  # type: ignore

        seller: Maker = Maker.objects.filter(
            bot=bot,
            is_buyer=False,
            base_token=Address(self.data.get("base_token", "")),
            quote_token=Address(self.data.get("quote_token", "")),
        ).first()  # type: ignore

        buyer.filled = F("amount") / 2
        seller.filled = F("amount") / 2
        Maker.objects.bulk_update([buyer, seller], fields=["filled"])

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(
            reverse("api:bot"), {"chain_id": self.data["chain_id"]}
        )
        data = response.json()

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The bot retrieval request should be successfull",
        )

        del self.data["signature"]

        self.data["is_buyer"] = int(not self.data["is_buyer"])
        self.data.update(
            {
                "bot_hash": str(
                    Web3.to_hex(
                        Web3.keccak(encode_order(self.data | {"replace_order": True}))
                    )
                ),
                "base_token_amount": "{0:f}".format(Decimal("9e18")),
                "quote_token_amount": "{0:f}".format(
                    Decimal("9e18")
                    - ((buyer.price * buyer.amount / 2) / Decimal("1e18")).quantize(
                        Decimal("1.")
                    )
                ),
                "fees_earned": "0",
            }
        )
        del self.data["is_buyer"]

        self.data["base_token"] = Address(self.data.get("base_token", ""))
        self.data["address"] = Address(self.data.get("address", ""))
        self.data["quote_token"] = Address(self.data.get("quote_token", ""))
        bot_timestamp = data[0]["timestamp"]
        del data[0]["timestamp"]

        self.assertEqual(len(data), 1, "only one bot should be available for the user")
        self.assertDictEqual(
            data[0],
            self.data,
            "The returned data shold contain the bot informations with the filled update",
        )

        self.assertAlmostEqual(
            self.timestamp,
            bot_timestamp,
            delta=1,
            msg="The returned bot timestamp should match the creation timestamp",
        )

    def test_bot_retrieval_with_two_bots_works(self):
        """Checks getting the user bot while having two bots works"""

        timestamp = int(time())
        data = {
            "address": Address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8"),
            "chain_id": 31337,
            "expiry": 2114380801,
            "signature": "0xbf7645fa71f5c170b5c41ff81aea9d3c71e8c8746d415149210d6cf9f2755bfe49a2ddf50532a8c8ab2f566c910d02705296a1574b30c57dad35025412a407791c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("1e18")),
            "base_token": Address("0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF"),
            "quote_token": Address("0x345CA3e014Aaf5dcA488057592ee47305D9B3e10"),
        }
        self.client.post(reverse("api:bot"), data=data)

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(
            reverse("api:bot"), {"chain_id": self.data["chain_id"]}
        )
        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "the request with the user having two bots should works",
        )

        del self.data["signature"], data["signature"]
        self.data["is_buyer"] = int(not self.data["is_buyer"])
        data["is_buyer"] = int(not data["is_buyer"])

        self.data.update(
            {
                "bot_hash": str(
                    Web3.to_hex(
                        Web3.keccak(encode_order(self.data | {"replace_order": True}))
                    )
                ),
                "base_token_amount": "{0:f}".format(Decimal("10e18")),
                "quote_token_amount": "{0:f}".format(Decimal("9e18")),
                "fees_earned": "0",
            }
        )

        data.update(
            {
                "bot_hash": str(
                    Web3.to_hex(
                        Web3.keccak(encode_order(data | {"replace_order": True}))
                    )
                ),
                "base_token_amount": "{0:f}".format(Decimal("5e18")),
                "quote_token_amount": "{0:f}".format(Decimal("45e17")),
                "fees_earned": "0",
            }
        )
        del self.data["is_buyer"], data["is_buyer"]

        (bot1, bot2) = sorted(
            response.json(), key=lambda b: int(b["base_token_amount"])
        )

        data["base_token"] = Address(data.get("base_token", ""))
        self.data["base_token"] = Address(self.data.get("base_token", ""))
        data["address"] = Address(data.get("address", ""))
        self.data["address"] = Address(self.data.get("address", ""))
        data["quote_token"] = Address(data.get("quote_token", ""))
        self.data["quote_token"] = Address(self.data.get("quote_token", ""))

        bot1_timestamp = bot1["timestamp"]
        bot2_timestamp = bot2["timestamp"]
        del bot1["timestamp"]
        del bot2["timestamp"]

        self.assertDictEqual(
            bot1,
            data,
            "The first bot should have the right amounts of base and quote token",
        )

        self.assertDictEqual(
            bot2,
            self.data,
            "The second bot should have the right amounts of base and quote token",
        )

        self.assertAlmostEqual(
            timestamp,
            bot1_timestamp,
            delta=3,
            msg="The returned bot1 timestamp should match the creation timestamp",
        )

        self.assertAlmostEqual(
            self.timestamp,
            bot2_timestamp,
            delta=3,
            msg="The returned bot2 timestamp should match the creation timestamp",
        )
