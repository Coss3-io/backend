from rest_framework.test import APITestCase
from api.models import User

class ReplacementOrdersCreationTestCase(APITestCase):
    """Class used for the testing of the bot creation"""

    def test_create_a_bot(self):
        """Checks the bot creation works well""" 

        