from rest_framework import serializers
from models import User

class UserSerializer(serializers.ModelSerializer):
    """The user class serializer"""

    class Meta:
        model = User