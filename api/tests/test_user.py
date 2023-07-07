from asgiref.sync import async_to_sync
from django.urls import reverse
from django.conf import settings
import api.errors as errors
from api.models import User
from api.models.types import Address
from rest_framework.test import APITestCase
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST


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
