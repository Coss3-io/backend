import hmac
from json import dumps
from time import time
from decimal import Decimal
from asgiref.sync import async_to_sync
from django.urls import reverse
from django.conf import settings
from web3 import Web3
from rest_framework import exceptions
from rest_framework.test import APITestCase
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from api.models.stacking import Stacking, StackingFees
from api.models.types import Address
from api.models import User
import api.errors as errors


class StackingTestCase(APITestCase):
    """Class used to test the behaviour of the creation of new
    stacking entries
    """

    def setUp(self) -> None:
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xC5Fdf4076b8F3A5357c5E395ab970B5B54098Fef")
        )

    def test_stacking_entries_creation_from_wt_work(self):
        """Checks stacking entries creation works well"""

        data = {
            "address": "0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking"), data=data)
        stack_entry = Stacking.objects.get(
            user__address=Web3.to_checksum_address(data["address"])
        )

        self.assertEqual(
            response.status_code, HTTP_200_OK, "the stacking entry creation should work"
        )
        self.assertDictEqual(
            response.json(), {}, "no data should be returned on stacking entry creation"
        )
        self.assertEqual(
            stack_entry.amount,
            Decimal(data["amount"]),
            "The amount of the stacking entry should match the amount sent",
        )

        self.assertEqual(
            stack_entry.slot,
            Decimal(data["slot"]),
            "The slot of the stacking entry should match the slot sent",
        )

    def test_stacking_entry_update_from_wt(self):
        """Checks the stacking entry update from watch tower works"""

        data = {
            "address": "0xC5FdF4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
        }

        Stacking.objects.create(amount=Decimal("239e18"), slot=23, user=self.user)

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking"), data=data)
        stack_entry = Stacking.objects.get(
            user__address=Web3.to_checksum_address(data["address"])
        )

        self.assertEqual(
            response.status_code, HTTP_200_OK, "the stacking entry update should work"
        )
        self.assertDictEqual(
            response.json(), {}, "no data should be returned on stacking entry update"
        )
        self.assertEqual(
            stack_entry.amount,
            Decimal(data["amount"]),
            "The amount of the stacking entry update should match the amount sent",
        )

        self.assertEqual(
            stack_entry.slot,
            Decimal(data["slot"]),
            "The slot of the stacking entry update should match the slot sent",
        )

    def test_stacking_creation_wrong_signature_fails(self):
        """Checks a stacking entry creation with wrong signature
        fails
        """

        data = {
            "address": "0xC5fdf4076B8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()
        data["signature"] = data["signature"][:-5] + "aaaaa"

        response = self.client.post(reverse("api:stacking"), data=data)

        self.assertDictEqual(
            response.json(),
            {"detail": errors.Permissions.WATCH_TOWER_AUTH_FAIL},
            "The stacking entry creation should fail with a wrong signature",
        )

        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The request should not be allowed with a wrong signature",
        )

    def test_stacking_user_creation_new_entry(self):
        """Checks if the user does not exist it is created
        on new stacking entry
        """

        data = {
            "address": "0xC5fdf4076b8f3A5357c5E395ab970B5B54098Fea",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The request with a non existing user should work",
        )

        User.objects.get(address=Web3.to_checksum_address(data["address"]))

    def test_stacking_entry_creation_wrong_address_fails(self):
        """Checks creating a stacking entry with a wrong address fails"""

        data = {
            "address": "0xZ5fdf4076b8F3A5357C5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("193e16")),
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request should fail with wrong address",
        )

        self.assertDictEqual(
            response.json(),
            {"address": [errors.Address.WRONG_ADDRESS_ERROR.format("")]},
        )

    def test_stacking_entry_creation_empty_address(self):
        """Checks stacking entry creation with empty address fails"""

        data = {
            # "address": "0xZ5fdf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("193e16")),
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request should fail with empty address",
        )

        self.assertDictEqual(
            response.json(),
            {"address": [errors.General.MISSING_FIELD]},
        )

    def test_stacking_entry_creation_wrong_slot(self):
        """Checks stacking creation with a wrong slot does not work"""

        data = {
            "address": "0xC5fdf4076b8F3A5357c5e395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("193e16")),
            "slot": "a23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking"), data=data)

        self.assertDictEqual(
            response.json(),
            {"slot": ["A valid integer is required."]},
            "the response should contain details about the error",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the request with a wrong slot should fail",
        )

    def test_stacking_entry_creation_empty_slot(self):
        """Checks stacking creation with a empty slot does not work"""

        data = {
            "address": "0xC5fdf4076b8F3a5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("193e16")),
            # "slot": "a23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking"), data=data)

        self.assertDictEqual(
            response.json(),
            {"slot": [errors.General.MISSING_FIELD]},
            "the response should contain details about the missing slot error",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the request with an empty slot should fail",
        )


class StackingRetrievalTestCase(APITestCase):
    """Class used to test the retrieval of stacking behaviour"""

    def setUp(self):
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef")
        )

        self.user_2 = async_to_sync(User.objects.create_user)(
            address=Address("0xA5fdf4076b8F3A5357C5E395ab970B5B54098Fef")
        )

        self.stacking_3 = Stacking.objects.create(
            amount=Decimal("21e18"), slot=21, user=self.user_2
        )

        self.stacking_1 = Stacking.objects.create(
            amount=Decimal("23e18"), slot=23, user=self.user
        )
        self.stacking_2 = Stacking.objects.create(
            amount=Decimal("134e17"), slot=12, user=self.user
        )

    def test_stacking_retrieval_works(self):
        """Checks stacking retrieval works for authenticated user"""

        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(reverse("api:stacking"))

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The stacking entries retrieval should work",
        )

        self.assertEqual(
            len(response.json()), 2, "Two entries should be returned by the server"
        )

        response = response.json()
        if response[0]["slot"] != 23:
            self.stacking_1, self.stacking_2 = self.stacking_2, self.stacking_1

        self.assertDictEqual(
            response[0],
            {
                "slot": self.stacking_1.slot,
                "amount": "{0:f}".format(self.stacking_1.amount),
            },
            "The first stacking entry should match the one into the database",
        )

        self.assertDictEqual(
            response[1],
            {
                "slot": self.stacking_2.slot,
                "amount": "{0:f}".format(self.stacking_2.amount),
            },
            "The second stacking entry should match the one into the database",
        )

    def test_anon_users_cannot_retrieve_stacking(self):
        """Anonymous users should not be able to retrieve stacking entries"""

        response = self.client.get(reverse("api:stacking"))

        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The request without being authenticated should fail",
        )

        self.assertDictEqual(
            response.json(), {"detail": exceptions.NotAuthenticated.default_detail}
        )


class StackingFeesTestCase(APITestCase):
    """Class used to test the behaviour of the creation of new
    stacking fees entries
    """

    def test_stacking_fees_entries_creation_from_wt_work(self):
        """Checks stacking fees entries creation works well"""

        data = {
            "token": "0xC5FDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking-fees"), data=data)
        stack_fees_entry = StackingFees.objects.get(
            token=Web3.to_checksum_address(data["token"])
        )

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "the stacking fees entry creation should work",
        )
        self.assertDictEqual(
            response.json(),
            {},
            "no data should be returned on stacking fees entry creation",
        )
        self.assertEqual(
            stack_fees_entry.amount,
            Decimal(data["amount"]),
            "The amount of the stacking fees entry should match the amount sent",
        )

        self.assertEqual(
            stack_fees_entry.slot,
            Decimal(data["slot"]),
            "The slot of the stacking fees entry should match the slot sent",
        )

    def test_stacking_fees_entry_update_from_wt(self):
        """Checks the stacking fees entry update from watch tower works"""

        data = {
            "token": "0xC5FDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
        }

        StackingFees.objects.create(
            amount=Decimal("23e18"),
            slot=23,
            token=Web3.to_checksum_address(data["token"]),
        )

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking-fees"), data=data)
        stack_fees_entry = StackingFees.objects.get(
            token=Web3.to_checksum_address(data["token"])
        )

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "the stacking fees entry update should work",
        )
        self.assertDictEqual(
            response.json(),
            {},
            "no data should be returned on stacking fees entry update",
        )
        self.assertEqual(
            stack_fees_entry.amount,
            Decimal(data["amount"]),
            "The amount of the stacking fees entry update should match the amount sent",
        )

        self.assertEqual(
            stack_fees_entry.slot,
            Decimal(data["slot"]),
            "The slot of the stacking fees entry update should match the slot sent",
        )

    def test_stacking_fees_creation_wrong_signature_fails(self):
        """Checks a stacking fees entry creation with wrong signature
        fails
        """

        data = {
            "token": "0xC5FDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()
        data["signature"] = data["signature"][:-5] + "aaaaa"

        response = self.client.post(reverse("api:stacking-fees"), data=data)

        self.assertDictEqual(
            response.json(),
            {"detail": errors.Permissions.WATCH_TOWER_AUTH_FAIL},
            "The stacking fees entry creation should fail with a wrong signature",
        )

        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The request should not be allowed with a wrong signature",
        )

    def test_stacking_fees_entry_creation_wrong_address_fails(self):
        """Checks creating a stacking fees entry with a wrong address fails"""

        data = {
            "token": "0xZ5FDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("193e16")),
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking-fees"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request should fail with wrong address",
        )

        self.assertDictEqual(
            response.json(),
            {"token": [errors.Address.WRONG_ADDRESS_ERROR.format("token")]},
        )

    def test_stacking_fees_entry_creation_empty_token(self):
        """Checks stacking fees entry creation with empty address fails"""

        data = {
            # "token": "0xZ5fdf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("193e16")),
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking-fees"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request should fail with empty token address",
        )

        self.assertDictEqual(
            response.json(),
            {"token": [errors.General.MISSING_FIELD]},
        )

    def test_stacking_fees_entry_creation_wrong_slot(self):
        """Checks stacking fees creation with a wrong slot does not work"""

        data = {
            "token": "0xC5FDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("193e16")),
            "slot": "a23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking-fees"), data=data)

        self.assertDictEqual(
            response.json(),
            {"slot": ["A valid integer is required."]},
            "the response should contain details about the error",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the request with a wrong slot should fail",
        )

    def test_stacking_fees_entry_creation_empty_slot(self):
        """Checks stacking fees creation with an empty slot does not work"""

        data = {
            "token": "0xC5FDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("193e16")),
            # "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking-fees"), data=data)

        self.assertDictEqual(
            response.json(),
            {"slot": [errors.General.MISSING_FIELD]},
            "the response should contain details about the missing slot error",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the request with a empty slot should fail",
        )


class StackingFeesRetrievalTestCase(APITestCase):
    """Class used to test the retrieval of stacking fees behaviour"""

    def setUp(self):
        self.address_1 = Web3.to_checksum_address(
            "0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520"
        )
        self.address_2 = Web3.to_checksum_address(
            "0xC02aaA39b223fe8D0A0e5C4F27eAD9083C756Cc2"
        )

        self.stacking_fees_3 = StackingFees.objects.create(
            amount=Decimal("21e18"), slot=21, token=self.address_1
        )

        self.stacking_fees_1 = StackingFees.objects.create(
            amount=Decimal("23e18"), slot=23, token=self.address_2
        )
        self.stacking_fees_2 = StackingFees.objects.create(
            amount=Decimal("134e17"), slot=12, token=self.address_2
        )

    def test_stacking_fees_retrieval_works(self):
        """Checks stacking fees retrieval works"""

        response = self.client.get(reverse("api:stacking-fees"))

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "The stacking entries retrieval should work",
        )

        self.assertEqual(
            len(response.json()), 3, "Three entries should be returned by the server"
        )

        self.assertListEqual(
            sorted([hash(frozenset(item.items())) for item in response.json()]),
            sorted(
                [
                    hash(frozenset(item.items()))
                    for item in reversed(
                        [
                            {
                                "token": self.stacking_fees_1.token,
                                "amount": "{0:f}".format(self.stacking_fees_1.amount),
                                "slot": self.stacking_fees_1.slot,
                            },
                            {
                                "token": self.stacking_fees_2.token,
                                "amount": "{0:f}".format(self.stacking_fees_2.amount),
                                "slot": self.stacking_fees_2.slot,
                            },
                            {
                                "token": self.stacking_fees_3.token,
                                "amount": "{0:f}".format(self.stacking_fees_3.amount),
                                "slot": self.stacking_fees_3.slot,
                            },
                        ]
                    )
                ]
            ),
            "The stacking fees entries should match the one into the database",
        )
