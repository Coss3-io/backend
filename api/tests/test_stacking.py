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
from api.models.stacking import Stacking, StackingFees, StackingFeesWithdrawal
from rest_framework.serializers import BooleanField
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

    def test_stacking_entries_creation_from_wt_work_withdrawal(self):
        """Checks stacking entries creation works well"""

        data = {
            "address": "0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
            "withdraw": "1"
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()
        data["withdraw"] = int(data["withdraw"]) #type: ignore

        response = self.client.post(reverse("api:stacking"), data=data)
        stack_entry = Stacking.objects.get(user__address=Address(data["address"]))

        self.assertEqual(
            response.status_code, HTTP_200_OK, "the stacking entry creation should work"
        )
        self.assertDictEqual(
            response.json(), {}, "no data should be returned on stacking entry creation"
        )
        self.assertEqual(
            stack_entry.amount,
            -Decimal(data["amount"]),
            "The amount of the stacking entry should match the amount sent and wether its a withdraw or not",
        )

        self.assertEqual(
            stack_entry.slot,
            Decimal(data["slot"]),
            "The slot of the stacking entry should match the slot sent",
        )

    def test_stacking_entries_creation_from_wt_work_deposit(self):
        """Checks stacking entries creation works well"""

        data = {
            "address": "0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
            "withdraw": "0"
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()
        data["withdraw"] = int(data["withdraw"]) #type: ignore

        response = self.client.post(reverse("api:stacking"), data=data)
        stack_entry = Stacking.objects.get(user__address=Address(data["address"]))

        self.assertEqual(
            response.status_code, HTTP_200_OK, "the stacking entry creation should work"
        )
        self.assertDictEqual(
            response.json(), {}, "no data should be returned on stacking entry creation"
        )
        self.assertEqual(
            stack_entry.amount,
            Decimal(data["amount"]),
            "The amount of the stacking entry should match the amount sent and wether its a withdraw or not",
        )

        self.assertEqual(
            stack_entry.slot,
            Decimal(data["slot"]),
            "The slot of the stacking entry should match the slot sent",
        )

    def test_stacking_entry_update_from_wt_deposit(self):
        """Checks the stacking entry update from watch tower works"""

        initial_amount = Decimal("239e18")
        data = {
            "address": "0xC5FdF4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
            "withdraw": "0"
        }

        Stacking.objects.create(amount=initial_amount, slot=23, user=self.user)

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()
        data["withdraw"] = int(data["withdraw"]) #type: ignore

        response = self.client.post(reverse("api:stacking"), data=data)
        stack_entry = Stacking.objects.get(user__address=Address(data["address"]))

        self.assertEqual(
            response.status_code, HTTP_200_OK, "the stacking entry update should work"
        )
        self.assertDictEqual(
            response.json(), {}, "no data should be returned on stacking entry update"
        )
        self.assertEqual(
            stack_entry.amount,
            Decimal(data["amount"]) + initial_amount,
            "The amount of the stacking entry update should be added to the previous amount as its a deposit",
        )

        self.assertEqual(
            stack_entry.slot,
            Decimal(data["slot"]),
            "The slot of the stacking entry update should match the slot sent",
        )

    def test_stacking_entry_update_from_wt_withdraw(self):
        """Checks the stacking entry update from watch tower works"""

        initial_amount = Decimal("239e18")
        data = {
            "address": "0xC5FdF4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
            "withdraw": "1"
        }

        Stacking.objects.create(amount=initial_amount, slot=23, user=self.user)

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()
        data["withdraw"] = int(data["withdraw"]) #type: ignore

        response = self.client.post(reverse("api:stacking"), data=data)
        stack_entry = Stacking.objects.get(user__address=Address(data["address"]))

        self.assertEqual(
            response.status_code, HTTP_200_OK, "the stacking entry update should work"
        )
        self.assertDictEqual(
            response.json(), {}, "no data should be returned on stacking entry update"
        )
        self.assertEqual(
            stack_entry.amount,
            -Decimal(data["amount"]) + initial_amount,
            "The amount of the stacking entry update should be substracted to the previous amount as its a withdrawal",
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
            "withdraw": "1"
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
            "withdraw": "1"
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

        User.objects.get(address=Address(data["address"]))

    def test_stacking_entry_creation_wrong_address_fails(self):
        """Checks creating a stacking entry with a wrong address fails"""

        data = {
            "address": "0xZ5fdf4076b8F3A5357C5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("193e16")),
            "slot": "23",
            "withdraw": "1"
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
            "withdraw": "1"
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
            "withdraw": "1"
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
            "withdraw": "1"
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

    def test_stacking_entries_creation_empty_withdrawal(self):
        """Checks stacking entries creation fails without withdraw field"""

        data = {
            "address": "0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
            #"withdraw": "1"
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()
        #data["withdraw"] = int(data["withdraw"]) #type: ignore

        response = self.client.post(reverse("api:stacking"), data=data)

        self.assertDictEqual(
            response.json(),
            {"withdraw": [errors.General.MISSING_FIELD]},
            "the response should contain details about the missing withdraw error",
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "the request with an empty slot should fail",
        )

    def test_stacking_entries_creation_wrong_withdrawal(self):
        """Checks stacking entries creation doesn't work with wrong format withdrawal fieldƒ"""

        data = {
            "address": "0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef",
            "amount": "{0:f}".format(Decimal("173e16")),
            "slot": "23",
            "withdraw": "abc"
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
            {"withdraw": [BooleanField.default_error_messages["invalid"]]},
            "the response should contain details about the wrong withdraw error",
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
        stack_fees_entry = StackingFees.objects.get(token=Address(data["token"]))

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
            token=Address(data["token"]),
        )

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:stacking-fees"), data=data)
        stack_fees_entry = StackingFees.objects.get(token=Address(data["token"]))

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
        self.address_1 = Address("0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520")
        self.address_2 = Address("0xC02aaA39b223fe8D0A0e5C4F27eAD9083C756Cc2")

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


class StackingFeesWithdrawalTestCase(APITestCase):
    """Class used to test the behaviour of the publication of fees withdrawal"""

    def test_stacking_fees_withdrawal_entries_creation_from_wt_work(self):
        """Checks stacking fees withdrawal entries creation works well"""

        data = {
            "token": "0xC5FDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "address": "0xC6FDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:fees-withdrawal"), data=data)
        stack_fees_withdrawal = StackingFeesWithdrawal.objects.get(
            token=Address(data["token"])
        )

        self.assertEqual(
            response.status_code,
            HTTP_200_OK,
            "the stacking fees withdrawal entry creation should work",
        )
        self.assertDictEqual(
            response.json(),
            {},
            "no data should be returned on stacking fees withdrawal entry creation",
        )

        self.assertEqual(
            stack_fees_withdrawal.slot,
            Decimal(data["slot"]),
            "The slot of the stacking fees entry should match the slot sent",
        )

        self.assertEqual(
            stack_fees_withdrawal.user,
            User.objects.get(address=Address(data["address"])),
            "The user attached to the stacking fees withdrawal should correspond to the address sent",
        )

    def test_stacking_fees_withdrawal_entries_creation_wrong_signature_fails(self):
        """Checks stacking fees withdrawal entries creation with a wrong signature fails"""

        data = {
            "token": "0xC5FDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "address": "0xC6FDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        data["slot"] = "24"

        response = self.client.post(reverse("api:fees-withdrawal"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The stacking fees creation should fail with a wrong signature",
        )

        with self.assertRaises(User.DoesNotExist):
            User.objects.get(address=Address(data["address"]))

    def test_stacking_fees_withdrawal_entries_creation_wrong_token_fails(self):
        """Checks stacking fees withdrawal entries creation with a wrong token fails"""

        data = {
            "token": "0xCgFDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "address": "0xC6FDf4076b8F3A5357c5E395ab970B5B54098Fef",
            "slot": "23",
        }

        data["timestamp"] = str(int(time()) * 1000)
        data["signature"] = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(data).encode(),
            digestmod="sha256",
        ).hexdigest()

        response = self.client.post(reverse("api:fees-withdrawal"), data=data)

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The stacking fees creation should fail with a wrong token",
        )

        with self.assertRaises(User.DoesNotExist):
            User.objects.get(address=Address(data["address"]))


class GlobalStackingRetrievalTestCase(APITestCase):
    """Test case used to retrieve the aggregation of all the stacking entries for the users"""

    def setUp(self) -> None:
        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xC5fdF4076b8F3A5357c5E395ab970B5B54098Fef")
        )

        self.user_2 = async_to_sync(User.objects.create_user)(
            address=Address("0xA5fdf4076b8F3A5357C5E395ab970B5B54098Fef")
        )

        self.stacking_1_1 = Stacking.objects.create(
            amount=Decimal("23e18"), slot=23, user=self.user
        )
        self.stacking_1_2 = Stacking.objects.create(
            amount=-Decimal("46e18"), slot=23, user=self.user_2
        )

        self.stacking_2_1 = Stacking.objects.create(
            amount=Decimal("134e17"), slot=12, user=self.user
        )

        self.stacking_2_2 = Stacking.objects.create(
            amount=Decimal("13e17"), slot=12, user=self.user_2
        )

        self.stacking_3_1 = Stacking.objects.create(
            amount=-Decimal("21e18"), slot=21, user=self.user
        )

        self.stacking_3_2 = Stacking.objects.create(
            amount=Decimal("29e18"), slot=21, user=self.user_2
        )

    def test_global_stacking_retrieval_works(self):
        """Checks the global stacking retrieval works properly"""

        self.stacking_4_1 = Stacking.objects.create(
            amount=Decimal("4658e18"), slot=46, user=self.user
        )

        response = self.client.get(reverse("api:global-stacking"))
        data = response.json()

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The response should be successfull"
        )

        self.assertListEqual(
            data,
            [
                [
                    self.stacking_1_1.slot,
                    self.stacking_1_1.amount + self.stacking_1_2.amount,
                ],
                [
                    self.stacking_3_1.slot,
                    self.stacking_3_1.amount + self.stacking_3_2.amount,
                ],
                [
                    self.stacking_2_1.slot,
                    self.stacking_2_1.amount + self.stacking_2_2.amount,
                ],
            ],
        )

    def test_global_stacking_retrieval_caching_works(self):
        """Checks the caching mecanism for the staking retrieval works"""

        response = self.client.get(reverse("api:global-stacking"))
        data = response.json()

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The response should be successfull"
        )

        self.assertListEqual(
            data,
            [
                [
                    self.stacking_1_1.slot,
                    self.stacking_1_1.amount + self.stacking_1_2.amount,
                ],
                [
                    self.stacking_3_1.slot,
                    self.stacking_3_1.amount + self.stacking_3_2.amount,
                ],
                [
                    self.stacking_2_1.slot,
                    self.stacking_2_1.amount + self.stacking_2_2.amount,
                ],
            ],
        )
