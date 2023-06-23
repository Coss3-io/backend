import hmac
from json import dumps
from time import time
from decimal import Decimal
from asgiref.sync import async_to_sync
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APITestCase
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from api.models.stacking import Stacking
from api.models.types import Address
from api.models import User
import api.errors as errors


class StackingTestCase(APITestCase):
    """Class used to test the behaviour of the creation of new
    stacking entries and the retrieval of the existing ones
    """

    def setUp(self) -> None:
        async_to_sync(User.objects.create_user)(
            address=Address("0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef")
        )

    def test_stacking_entries_creation_from_wt_work(self):
        """Checks stacking entries creation works well"""

        data = {
            "address": "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef",
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
        stack_entry = Stacking.objects.get(user__address=data["address"])

        self.assertEqual(
            response.status_code, HTTP_200_OK, "the stacking entry update should work"
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

    def test_stacking_creation_wrong_signature_fails(self):
        """Checks a stacking entry creation with wrong signature
        fails
        """

        data = {
            "address": "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef",
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
            "address": "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fea",
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

        User.objects.get(address=data["address"])

    def test_stacking_entry_update(self):
        """Checks updating a stacking entry works"""

        data = {
            "address": "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef",
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
        stack_entry = Stacking.objects.get(
            user__address=data["address"], slot=data["slot"]
        )

        self.assertEqual(
            stack_entry.amount,
            Decimal(data["amount"]),
            "The amount of the stacking entry should be updated",
        )

        self.assertDictEqual(
            response.json(), {}, "No data should be returned on success"
        )

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The stacking entry update should work"
        )

    def test_stacking_entry_creation_wrong_address_fails(self):
        """Checks creating a stacking entry with a wrong address fails"""

        data = {
            "address": "0xZ5fdf4076b8F3A5357c5E395ab970B5B54098Fef",
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
            "address": "0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef",
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

        #self.assertDictEqual(response.json(), ) 