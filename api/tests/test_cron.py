from decimal import Decimal
from datetime import datetime
from time import time
from rest_framework.test import APITestCase
from backend.cron import deleting_expired_orders
from api.models import User
from api.models.types import Address
from asgiref.sync import async_to_sync
from api.models.orders import Maker


class CronjobTestCase(APITestCase):
    """Test cases for the cron job"""

    def setUp(self):
        """Populate with expired and not expired orders"""

        self.user = async_to_sync(User.objects.create_user)(
            address=Address("0xF17f52151EbEF6C7334FAD080c5704D77216b732")
        )

        self.maker1 = async_to_sync(Maker.objects.create)(
            user=self.user,
            amount="{0:f}".format(Decimal("185e11")),
            filled="{0:f}".format(Decimal("1e11")),
            expiry=datetime.fromtimestamp(int(time()) - 10),
            price="{0:f}".format(Decimal("173e18")),
            chain_id=1337,
            base_token="0x4ABeEB066eD09B7AEd07bF39EEe0460DFa261520",
            quote_token="0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520",
            signature="0xfabfac7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            order_hash="0x0e3c530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            is_buyer=False,
        )

        self.maker2 = async_to_sync(Maker.objects.create)(
            user=self.user,
            amount="{0:f}".format(Decimal("185e11")),
            filled="{0:f}".format(Decimal("1e11")),
            expiry=datetime.fromtimestamp(int(time()) + 10),
            price="{0:f}".format(Decimal("173e18")),
            chain_id=1337,
            base_token="0x4AceEB066eD09B7AEd07bF39EEe0460DFa261520",
            quote_token="0x4BBeEB066eD09B7AEd07bF39EEe0460DFa261520",
            signature="0xfabfbc7f7a8bbb7f87747c940a6a9be667a57c86c145fd2bb91d8286cdbde0253e1cf2c95bdfb87a46669bc8ba0d4f92b4786d00df7f90aea8004d2b953b27cb1b",
            order_hash="0x0e3a530932af2cadc56e2cb633b4a4952b5ebb74888c19e1068c2d0213953e45",
            is_buyer=False,
        )

    def test_cron_job_function(self):
        """Function used to check the cronjob behaviour"""

        deleting_expired_orders()
        self.assertRaises(Maker.DoesNotExist, self.maker1.refresh_from_db)
        self.maker2.refresh_from_db()
        self.assertEqual(
            self.maker2.is_buyer,
            False,
            "The not expired maker should still be into the database",
        )
