from django.urls import reverse
from django.conf import settings
import api.errors as errors
from api.models import User
from rest_framework.test import APITestCase
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST


class UserCreationTestCase(APITestCase):
    """Test case for user creation verifing the signature"""

    url = reverse("api:account")

    def test_regular_user_creation(self):
        """Checks the user creation works well"""

        signature = "0x740cf934332732702e8f5906a09690b76ff90148f6ba5e014864961a027537e61e8df72ee1e564788219c956a6b84567e0a370da604207e9694f70b94fe141e11c"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )

        self.assertEqual(
            response.status_code, HTTP_200_OK, "The user creation should not fail"
        )
        User.objects.get(address=address)

    def test_user_creation_old_timestamp(self):
        """Checks a user with a too old timestamp cannot be created"""

        signature = "0xacb8299160a6570f56ff85a0ac8f1aebb9bb0d4f19b059ee77bd042888a743445839938aff7ed52acdc433a7d4cc1728a08f4161ff1bcb8ac5a7f6018a6f9d301c"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = "211438080"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with an old timestamp should fail",
        )
        self.assertDictEqual(
            response.json(),
            {
                settings.REST_FRAMEWORK["NON_FIELD_ERRORS_KEY"]: [
                    errors.User.USER_TIMESTAMP_ERROR
                ]
            },
        )

    def test_user_creation_wrong_timestamp(self):
        """Checks sending a wrong timstamp does not allow user creation"""

        signature = "0xacb8299160a6570f56ff85a0ac8f1aebb9bb0d4f19b059ee77bd042888a743445839938aff7ed52acdc433a7d4cc1728a08f4161ff1bcb8ac5a7f6018a6f9d301c"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = "a"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a wrong timestamp should fail",
        )
        self.assertDictEqual(
            response.json(),
            {
                settings.REST_FRAMEWORK["NON_FIELD_ERRORS_KEY"]: [
                    errors.Decimal.WRONG_DECIMAL_ERROR.format("timestamp")
                ]
            },
        )

    def test_user_creation_0_timestamp(self):
        """Checks sending a 0 timstamp does not allow user creation"""

        signature = "0xacb8299160a6570f56ff85a0ac8f1aebb9bb0d4f19b059ee77bd042888a743445839938aff7ed52acdc433a7d4cc1728a08f4161ff1bcb8ac5a7f6018a6f9d301c"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = "0"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a 0 timestamp should fail",
        )
        self.assertDictEqual(
            response.json(),
            {
                settings.REST_FRAMEWORK["NON_FIELD_ERRORS_KEY"]: [
                    errors.Decimal.ZERO_DECIMAL_ERROR.format("timestamp")
                ]
            },
        )
