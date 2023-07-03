from decimal import Decimal
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.test import APITestCase
from rest_framework.serializers import DecimalField, BooleanField
from api.models import User
import api.errors as errors


class ReplacementOrdersCreationTestCase(APITestCase):
    """Class used for the testing of the bot creation"""

    def test_create_a_bot(self):
        """Checks the bot creation works well"""

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

        response = self.client.post(reverse("api:bot"), data=data)
        User.objects.get(address=data.get("address"))
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
                data.get("address"),
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
            else:
                self.assertEqual(
                    order.get("is_buyer"),
                    False,
                    "If the price is strictly above the threesold price, the order should be a sell",
                )

            self.assertEqual(
                order.get("step"),
                data.get("step"),
                "The step field should be reported into the orders created",
            )

            self.assertEqual(
                order.get("maker_fees"),
                data.get("maker_fees"),
                "The maker_fees field should be reported into the orders created",
            )

            self.assertIsNotNone(
                prices.index(order.get("price")),
                "The price of the order should be in the prices list",
            )
            prices.pop(prices.index(order.get("price")))

            self.assertEqual(
                order.get("lower_bound"),
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
                data.get("base_token"),
                "The orders base_token should match the bot base_token",
            )
            self.assertEqual(
                order.get("quote_token"),
                data.get("quote_token"),
                "The orders quote_token should match the bot quote_token",
            )

        self.assertListEqual(
            prices, [], "All the prices of the range should be into the orders"
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
            {"is_buyer": [BooleanField.error_messages["invalid"]]},  # type:ignore
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
            {"step": [DecimalField.error_messages["invalid"]]},  # type:ignore
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
            {"price": [DecimalField.error_messages["invalid"]]},  # type:ignore
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
            {"maker_fees": [DecimalField.error_messages["invalid"]]},  # type:ignore
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
            {"upper_bound": [DecimalField.error_messages["invalid"]]},  # type:ignore
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
            {"lower_bound": [DecimalField.error_messages["invalid"]]},  # type:ignore
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
            {"amount": [DecimalField.error_messages["invalid"]]},  # type:ignore
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
