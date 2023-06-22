import hmac
from json import dumps
from time import time
from decimal import Decimal
from asgiref.sync import async_to_sync
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APITestCase
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from api.models.stacking import Stacking
from api.models.types import Address
from api.models import User


class StackingTestCase(APITestCase):
    """Class used to test the behaviour of the creation of new
    stacking entries and the retrieval of the existing ones
    """

    def test_stacking_entries_creation_from_wt_work(self):
        """Checks stacking entries creation works well"""
        async_to_sync(User.objects.create_user)(
            address=Address("0xC5fdf4076b8F3A5357c5E395ab970B5B54098Fef")
        )
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
