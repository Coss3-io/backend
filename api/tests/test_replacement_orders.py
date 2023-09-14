from decimal import Decimal
from time import time
from asgiref.sync import async_to_sync
from django.urls import reverse
from django.db.models import F
from web3 import Web3
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from rest_framework.test import APITestCase
from rest_framework.serializers import DecimalField, BooleanField
from rest_framework.exceptions import NotAuthenticated
from api.models import User
from api.models.orders import Maker, Bot
from api.models.types import Address
import api.errors as errors


class ReplacementOrdersCreationTestCase(APITestCase):
    """Class used for the testing of the bot creation"""

    def test_create_a_bot(self):
        """Checks the bot creation works well"""
        timestamp = int(time())
        data = {
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

        response = self.client.post(reverse("api:bot"), data=data)
        base_token_amount = Decimal("0")
        quote_token_amount = Decimal("0")

        User.objects.get(address=Web3.to_checksum_address(data.get("address", "")))
        orders = self.client.get(
            reverse("api:orders"),
            data={
                "base_token": data.get("base_token"),
                "quote_token": data.get("quote_token"),
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
                order["address"],
                Web3.to_checksum_address(data.get("address", "")),
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
                Web3.to_checksum_address(data.get("base_token", "")),
                "The orders base_token should match the bot base_token",
            )
            self.assertEqual(
                order.get("quote_token"),
                Web3.to_checksum_address(data.get("quote_token", "")),
                "The orders quote_token should match the bot quote_token",
            )

        self.assertListEqual(
            prices, [], "All the prices of the range should be into the orders"
        )

        del data["expiry"]
        del data["signature"]
        del data["amount"]
        del data["is_buyer"]
        data["address"] = Web3.to_checksum_address(data.get("address", ""))
        data["base_token"] = Web3.to_checksum_address(data.get("base_token", ""))
        data["quote_token"] = Web3.to_checksum_address(data.get("quote_token", ""))

        bot_data = response.json()
        bot_timestamp = bot_data["timestamp"]
        del bot_data["timestamp"]
        data.update(
            {
                "base_token_amount": "{0:f}".format(base_token_amount),
                "quote_token_amount": "{0:f}".format(quote_token_amount),
                "fees_earned": "0",
            }
        )
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
            "timestamp": 200000
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0x0b0219373a4ae66877534990dad2e3376de8a456bc2a6bdf694fb8914456f1110a23d44fa11a5f025be0ebed89c56e41da70f42803dc70e858c7ad010f64cc641b",
            "is_buyer": False,
            "step": "0",
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe85fcb21e2409140501d4864c76f2dbe85e3bd22627ea596cb84ef5fdbf4cfd41650d2270fe33577415cb3204c3ede0818bc22b81853b94231abfaa926a7da6e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "0",  # "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
        """Creating a bot with a 0 price should not be allowed"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xcbd9aab47e61f1dfeea5ab2ab67d74a5ad327dc727890fbd0b94baee1aa2c0542bcb5d6ebc07dbbbffa568ead302511d2c83781c287cf95b849956df177d09b01b",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "0",  # "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        response = self.client.post(reverse("api:bot"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a 0 price field should fail",
        )

        self.assertDictEqual(
            response.json(),
            {"price": [errors.Decimal.ZERO_DECIMAL_ERROR.format("price")]},
            "the error returned should be about the 0 amount field",
        )

    def test_creating_a_bot_same_base_and_quote_fails(self):
        """Checks that creating a bot with the same base and the same quote fails"""

        data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0x99afc3b74a0a04cbbaa84479ee95a4cb2f5527bb491fc85b6178596b28944bc55f3b1438a6d8963c2b9421e6cc5942c340eea8924c3f23d384a0f204729ad5121c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xb35fef1442e7a63a165f4da7c6d460f94c3d090596f7b3323ef14ada90ffa7f7209565892d4673247595a4ced71ce2b940dc126f9b40c198bc0a12e3b4ca6fc11c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e19")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0x5434e66fb93872d2779023d9b706f8181bcbc07a808e37ac0846ef6587daf0c86893375542b606ab11f9276be23f0a144d5818a3eb5054efa2ab740a54a0ad361c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("11e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0x363bfa68e74b9351338923fa184f09a536fbb9ac59342e2bd73f526159e301ef03982a522aade72cb3e90f808aee53d73ee2a710d1de153bfaac07fdf8a7a62b1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("1e18")),
            "lower_bound": "{0:f}".format(Decimal("1e18")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
        }

        maker_data = {
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "amount": "{0:f}".format(Decimal("173e16")),
            "expiry": 2114380800,
            "price": "{0:f}".format(Decimal("2e20")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
            "signature": "0xd71e912a471c9d6df869a636e05adee17d1df3f4e929c030992bef54b35ddee93a3207665ee47ef9f4b09daf39d52f15007e5035fc391a65c7db0eb6f6ee60651c",
            "order_hash": "0xd08bcea784907c943819f0e99571bbf34e01abce3d288528dee96da4f3eb868b",
            "is_buyer": False,
        }
        response = self.client.post(reverse("api:order"), data=maker_data)
        self.client.post(reverse("api:bot"), data=data)

        orders = self.client.get(
            reverse("api:orders"),
            data={
                "base_token": data.get("base_token"),
                "quote_token": data.get("quote_token"),
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
            # "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0x17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xff17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xz17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            # "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "expiry": "a2114380800",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            # "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": "drengrtw",
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            # "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0x92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xee92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xz92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xa92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            # "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "a" + "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            # "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "a" + "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            # "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "a" + "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            # "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "a" + "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            # "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("5e17")),
            "lower_bound": "a" + "{0:f}".format(Decimal("15e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            # "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "a" + "{0:f}".format(Decimal("2e18")),
            "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            # "base_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xz25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0x25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "base_token": "0xff25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            # "quote_token": "0xf25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "base_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "quote_token": "0xz25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "base_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "quote_token": "0x25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "base_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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
            "address": "0xf17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380800,
            "signature": "0xe92e492753888a2891e6ea28e445c952f08cb1fc67a75d8b91b89a70a1f4a86052233756c00ca1c3019de347af6ea15a3fbfb7c164d2468456aae2481105f70e1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("2e18")),
            "quote_token": "0xff25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "base_token": "0x345cA3e014Aaf5dcA488057592ee47305D9B3e10",
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


class BotRetrievalTestCase(APITestCase):
    """Class used to test the retrieval of the users bots"""

    def setUp(self):
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xf17f52151EbEF6C7334FAD080c5704D77216b732")
        )
        self.timestamp = int(time())
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

    def test_retrieving_user_bots_works(self):
        """Checks retrieving the bots of a user works"""

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:bot"))
        data = response.json()
        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The bot retrieval request should be successfull",
        )

        del self.data["expiry"]
        del self.data["signature"]
        del self.data["amount"]
        del self.data["is_buyer"]

        self.data["base_token"] = Web3.to_checksum_address(
            self.data.get("base_token", "")
        )
        self.data["quote_token"] = Web3.to_checksum_address(
            self.data.get("quote_token", "")
        )
        self.data["address"] = Web3.to_checksum_address(self.data.get("address", ""))
        
        bot_timestamp = data[0]["timestamp"]
        del data[0]["timestamp"]

        self.data.update(
            {
                "base_token_amount": "{0:f}".format(Decimal("10e18")),
                "quote_token_amount": "{0:f}".format(Decimal("9e18")),
                "fees_earned": "0",
            }
        )

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

        response = self.client.get(reverse("api:bot"))

        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The non auth user should not be able to view bots ",
        )

        self.assertDictEqual(
            response.json(), {"detail": NotAuthenticated.default_detail}
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
            base_token=Web3.to_checksum_address(self.data.get("base_token", "")),
            quote_token=Web3.to_checksum_address(self.data.get("quote_token", "")),
        ).first()  # type: ignore

        seller: Maker = Maker.objects.filter(
            bot=bot,
            is_buyer=False,
            base_token=Web3.to_checksum_address(self.data.get("base_token", "")),
            quote_token=Web3.to_checksum_address(self.data.get("quote_token", "")),
        ).first()  # type: ignore

        buyer.filled = F("amount") / 2
        seller.filled = F("amount") / 2
        Maker.objects.bulk_update([buyer, seller], fields=["filled"])

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:bot"))
        data = response.json()

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The bot retrieval request should be successfull",
        )

        del self.data["expiry"]
        del self.data["signature"]
        del self.data["amount"]
        del self.data["is_buyer"]

        self.data.update(
            {
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

        self.data["base_token"] = Web3.to_checksum_address(
            self.data.get("base_token", "")
        )
        self.data["address"] = Web3.to_checksum_address(self.data.get("address", ""))
        self.data["quote_token"] = Web3.to_checksum_address(
            self.data.get("quote_token", "")
        )
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
            "address": "0xF17f52151EbEF6C7334FAD080c5704D77216b732",
            "expiry": 2114380801,
            "signature": "0x201a1a4decd1b648366cd1c3577f3f7e21f8064836b8b8543bd93fbe6be33f2104935687856f2fd5dd355b277ac5f826e14e068c3e63b15f0d8412665cbcdced1c",
            "is_buyer": False,
            "step": "{0:f}".format(Decimal("1e17")),
            "price": "{0:f}".format(Decimal("1e18")),
            "maker_fees": "{0:f}".format(Decimal("50")),
            "upper_bound": "{0:f}".format(Decimal("15e17")),
            "lower_bound": "{0:f}".format(Decimal("5e17")),
            "amount": "{0:f}".format(Decimal("1e18")),
            "base_token": "0xF25186B5081Ff5cE73482AD761DB0eB0d25abfBF",
            "quote_token": "0x345cA3E014Aaf5dcA488057592ee47305D9B3e10",
        }
        self.client.post(reverse("api:bot"), data=data)

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:bot"))
        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "the request with the user having two bots should works",
        )

        del self.data["expiry"], data["expiry"]
        del self.data["signature"], data["signature"]
        del self.data["amount"], data["amount"]
        del self.data["is_buyer"], data["is_buyer"]

        self.data.update(
            {
                "base_token_amount": "{0:f}".format(Decimal("10e18")),
                "quote_token_amount": "{0:f}".format(Decimal("9e18")),
                "fees_earned": "0",
            }
        )

        data.update(
            {
                "base_token_amount": "{0:f}".format(Decimal("5e18")),
                "quote_token_amount": "{0:f}".format(Decimal("45e17")),
                "fees_earned": "0",
            }
        )

        (bot1, bot2) = sorted(
            response.json(), key=lambda b: int(b["base_token_amount"])
        )

        data["base_token"] = Web3.to_checksum_address(data.get("base_token", ""))
        self.data["base_token"] = Web3.to_checksum_address(
            self.data.get("base_token", "")
        )
        data["address"] = Web3.to_checksum_address(data.get("address", ""))
        self.data["address"] = Web3.to_checksum_address(self.data.get("address", ""))
        data["quote_token"] = Web3.to_checksum_address(data.get("quote_token", ""))
        self.data["quote_token"] = Web3.to_checksum_address(
            self.data.get("quote_token", "")
        )

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
            delta=1,
            msg="The returned bot1 timestamp should match the creation timestamp",
        )

        self.assertAlmostEqual(
            self.timestamp,
            bot2_timestamp,
            delta=1,
            msg="The returned bot2 timestamp should match the creation timestamp",
        )
