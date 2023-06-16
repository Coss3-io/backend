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

    def test_user_creation_short_address(self):
        """Checks sending a too short address does not allow user creation"""

        signature = "0x740cf934332732702e8f5906a09690b76ff90148f6ba5e014864961a027537e61e8df72ee1e564788219c956a6b84567e0a370da604207e9694f70b94fe141e11c"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b73"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a short address shoul fail",
        )
        self.assertDictEqual(
            response.json(),
            {"address": ["Ensure this field has at least 42 characters."]},
        )

    def test_user_creation_long_address(self):
        """Checks sending a too long address does not allow user creation"""

        signature = "0x740cf934332732702e8f5906a09690b76ff90148f6ba5e014864961a027537e61e8df72ee1e564788219c956a6b84567e0a370da604207e9694f70b94fe141e11c"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b73aa"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a long address should fail",
        )
        self.assertDictEqual(
            response.json(),
            {"address": ["Ensure this field has no more than 42 characters."]},
        )

    def test_user_creation_wrong_address(self):
        """Checks sending a wrong address does not allow user creation"""

        signature = "0x740cf934332732702e8f5906a09690b76ff90148f6ba5e014864961a027537e61e8df72ee1e564788219c956a6b84567e0a370da604207e9694f70b94fe141e11c"
        address = "0xz17f52151EbEF6C7334FAD080c5704D77216b731"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a wrong address should fail",
        )
        self.assertDictEqual(
            response.json(),
            {
                settings.REST_FRAMEWORK["NON_FIELD_ERRORS_KEY"]: [
                    errors.Address.WRONG_ADDRESS_ERROR.format("")
                ]
            },
        )

    def test_user_creation_short_signature(self):
        """Checks sending a too short signature does not allow user creation"""

        signature = "0x74cf934332732702e8f5906a09690b76ff90148f6ba5e014864961a027537e61e8df72ee1e564788219c956a6b84567e0a370da604207e9694f70b94fe141e11c"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b731"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a short signature should fail",
        )
        self.assertDictEqual(
            response.json(),
            {
                settings.REST_FRAMEWORK["NON_FIELD_ERRORS_KEY"]: [
                    errors.Signature.SHORT_SIGNATURE_ERROR
                ]
            },
        )

    def test_user_creation_long_signature(self):
        """Checks sending a too long signature does not allow user creation"""

        signature = "0x7400cf934332732702e8f5906a09690b76ff90148f6ba5e014864961a027537e61e8df72ee1e564788219c956a6b84567e0a370da604207e9694f70b94fe141e11c"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b731"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a too long signature should fail",
        )
        self.assertDictEqual(
            response.json(),
            {
                settings.REST_FRAMEWORK["NON_FIELD_ERRORS_KEY"]: [
                    errors.Signature.LONG_SIGNATURE_ERROR
                ]
            },
        )

    
    def test_user_creation_wrong_signature(self):
        """Checks sending a wrong signature does not allow user creation"""

        signature = "0x74zcf934332732702e8f5906a09690b76ff90148f6ba5e014864961a027537e61e8df72ee1e564788219c956a6b84567e0a370da604207e9694f70b94fe141e11c"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b731"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a wrong signature should fail",
        )
        self.assertDictEqual(
            response.json(),
            {
                settings.REST_FRAMEWORK["NON_FIELD_ERRORS_KEY"]: [
                    errors.Signature.WRONG_SIGNATURE_ERROR
                ]
            },
        )

    def test_user_creation_mismatch_signature(self):
        """Checks sending a mismatch signature does not allow user creation"""

        signature = "0x741cf934332732702e8f5906a09690b76ff90148f6ba5e014864961a027537e61e8df72ee1e564788219c956a6b84567e0a370da604207e9694f70b94fe141e11c"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b731"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The request with a mismatch signature should fail",
        )
        self.assertDictEqual(
            response.json(),
            {
                settings.REST_FRAMEWORK["NON_FIELD_ERRORS_KEY"]: [
                    errors.Signature.SIGNATURE_MISMATCH_ERROR
                ]
            },
        )

