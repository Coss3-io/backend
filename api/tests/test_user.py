from asgiref.sync import async_to_sync
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.conf import settings
import api.errors as errors
from api.models import User
from api.models.types import Address
from rest_framework.test import APITestCase
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN


class UserCreationTestCase(APITestCase):
    """Test case for user creation verifing the signature"""

    url = reverse("api:account")

    def test_regular_user_creation(self):
        """Checks the user creation works well"""

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
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

    def test_user_creation_twice_fails_identical_address(self):
        """Checks we cannot create the same user twice"""

        async_to_sync(User.objects.create_user)(
            address=Address("0xf17f52151EbEF6C7334FAD080c5704D77216b732")
        )

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "User creation twice should not work",
        )

        self.assertDictEqual(
            response.json(), {"address": ["user with this address already exists."]}
        )

    def test_user_creation_twice_fails_case_different_address(self):
        """Checks we cannot create the same user twice event with address of different case"""

        async_to_sync(User.objects.create_user)(
            address=Address("0xf17f52151EbEF6C7334FAD080c5704D77216b732")
        )

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216B732"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address, "timestamp": timestamp},
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "User creation twice should not work even with different case address",
        )

        self.assertDictEqual(
            response.json(), {"address": ["user with this address already exists."]}
        )

    def test_user_creation_old_timestamp(self):
        """Checks a user with a too old timestamp cannot be created"""

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
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
            {"timestamp": [errors.User.USER_TIMESTAMP_ERROR]},
        )

    def test_user_creation_wrong_timestamp(self):
        """Checks sending a wrong timstamp does not allow user creation"""

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
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
            {"timestamp": [errors.Decimal.WRONG_DECIMAL_ERROR.format("timestamp")]},
        )

    def test_user_creation_0_timestamp(self):
        """Checks sending a 0 timstamp does not allow user creation"""

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
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
            {"timestamp": [errors.Decimal.ZERO_DECIMAL_ERROR.format("timestamp")]},
        )

    def test_user_creation_short_address(self):
        """Checks sending a too short address does not allow user creation"""

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
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

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
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

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
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
            {"address": [errors.Address.WRONG_ADDRESS_ERROR.format("")]},
        )

    def test_user_creation_short_signature(self):
        """Checks sending a too short signature does not allow user creation"""

        signature = "0x41d75e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
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

        signature = "0x41dd725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
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

        signature = "0x41z725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
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

        signature = "0x41a725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
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

    def test_user_creation_missing_timestamp(self):
        """Checks we cannot create a user without sending a timestamp"""

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "address": address},
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The user creation without timestamp should not work",
        )

        self.assertDictEqual(
            response.json(),
            {"timestamp": [errors.Decimal.ZERO_DECIMAL_ERROR.format("timestamp")]},
        )

    def test_user_creation_missing_address(self):
        """Checks we cannot create a user without sending an address"""

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"signature": signature, "timestamp": timestamp},
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The user creation without address should not work",
        )

        self.assertDictEqual(
            response.json(),
            {"address": ["This field may not be blank."]},
        )

    def test_user_creation_missing_signature(self):
        """Checks we cannot create a user without sending a signature"""

        signature = "0x41d725e42c47ea30d326e1a8fc48a234ec4445aebe34f3bb3c0547603208a5947365b2de6f777db2982672ed040824500f46253694d176905219354740261c3f1b"
        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = "2114380800"

        response = self.client.post(
            self.url,
            data={"address": address, "timestamp": timestamp},
        )
        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The user creation without signature should not work",
        )

        self.assertDictEqual(
            response.json(),
            {"error": [errors.Signature.SHORT_SIGNATURE_ERROR]},
        )


class UserLogInTestCase(APITestCase):
    """Test the behaviour of the user log in"""

    def test_user_log_in_works(self):
        """Checks a well formed request allows the user to log in"""

        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = "2114380800"
        signature = "0xcd831a961d3c4d71a7abc6dc83a0cb3ab130c4894a668873907bef9ec6be285e6da54e6955bfa95bd5e4c94f0859b82a8dd5ad534b1b567a9d5704945d86b9551c"

        response = self.client.get(reverse("api:order"), data={"all": True})
        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The request without being logged in should be forbodde",
        )

        with patch("api.views.user.time", return_value=2114380800):
            response = self.client.post(
                reverse("api:login"),
                data={
                    "address": address,
                    "timestamp": timestamp,
                    "signature": signature,
                },
            )

        self.assertDictEqual(
            response.json(), {}, "The response on log in should be empty"
        )
        self.assertEqual(
            response.status_code, HTTP_200_OK, "The request should be succesfull"
        )

        response = self.client.get(reverse("api:order"), data={"all": True})
        self.assertEqual(
            response.status_code, HTTP_200_OK, "The user should be logged in "
        )

    def test_user_log_in_missing_address(self):
        """Checks the user log in without address fails"""

        address = "0xf17f52151EbEF6C7334FAD080c5704D77216b732"
        timestamp = "2114380800"
        signature = "0xcd831a961d3c4d71a7abc6dc83a0cb3ab130c4894a668873907bef9ec6be285e6da54e6955bfa95bd5e4c94f0859b82a8dd5ad534b1b567a9d5704945d86b9551c"

        response = self.client.get(reverse("api:order"), data={"all": True})
        self.assertEqual(
            response.status_code,
            HTTP_403_FORBIDDEN,
            "The request without being logged in should be forbodde",
        )

        with patch("api.views.user.time", return_value=2114380800):
            response = self.client.post(
                reverse("api:login"),
                data={
                    # "address": address,
                    "timestamp": timestamp,
                    "signature": signature,
                },
            )

        self.assertEqual(
            response.status_code,
            HTTP_400_BAD_REQUEST,
            "The login request without address should fail",
        )
        self.assertDictEqual(
            response.json(), {"address": [errors.General.MISSING_FIELD]}
        )
