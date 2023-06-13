from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

class MakerOrderTestCase(APITestCase):
    """Test case for creating an retrieving Maker orders"""

    def test_creating_maker_order_works(self):
        """Checks we can create an order"""

        