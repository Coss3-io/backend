from django.conf import settings
from rest_framework import authentication
from rest_framework import exceptions
from api.utils import validate_user


class ApiAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        if not request.query_params.get("signature", ""):
            return None
        success, result = validate_user(
            request.query_params,
            settings.API_LOG_IN_MESSAGE.format(
                method=request.method, path=request.path
            ),
        )
        if not success:
            raise exceptions.AuthenticationFailed(result)
        result.__setattr__("is_authenticated",True) 
        return result, "awaitable"
