import hmac
from time import time
from json import dumps
from django.conf import settings
from rest_framework.permissions import BasePermission


class WatchTowerPermission(BasePermission):
    """Class used to restrict some view only to the watch tower"""

    def has_permission(self, request, view):
        if not (signature := request.data.get("signature", None)):
            return False
        if not (user_timestamp := request.data.get("timestamp", None)):
            return False

        del request.data["signature"]
        del request.data["timestamp"]
        timestamp = int(time()) * 1000

        if timestamp - user_timestamp > 10000:
            return False

        digest = hmac.new(
            key=settings.WATCH_TOWER_KEY.encode(),
            msg=dumps(request.data).encode(),
            digestmod="SHA256",
        ).hexdigest()

        return hmac.compare_digest(digest, signature)
