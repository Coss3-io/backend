import hmac
from time import time
from json import dumps
from django.conf import settings
from api.utils import validate_decimal_integer
import api.errors as errors
from rest_framework.permissions import BasePermission


class WatchTowerPermission(BasePermission):
    """Class used to restrict some view only to the watch tower"""

    message = errors.Permissions.WATCH_TOWER_AUTH_FAIL

    def has_permission(self, request, view):
        if not (signature := request.data.get("signature", None)):
            return False
        if not (
            user_timestamp := int(
                validate_decimal_integer(
                    request.data.get("timestamp", 0), name="timestamp"
                )
            )
        ):
            request.authenticators = []
            return False
        
        if request.data.get("_mutable", None):
            request.data._mutable = True
            del request.data["signature"]
            request.data._mutable = False
        else: 
            del request.data["signature"]

        timestamp = int(time()) * 1000

        if timestamp - user_timestamp > 3000:
            request.authenticators = []
            return False

        digest = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(request.data).encode(),
            digestmod="sha256",
        ).hexdigest()

        if hmac.compare_digest(digest, signature):
            return True
        else:
            request.authenticators = []
            return False
