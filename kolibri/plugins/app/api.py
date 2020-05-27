from django.http import HttpResponseRedirect
from django.utils.http import is_safe_url
from django.utils.http import urlunquote
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from kolibri.core.device.models import DeviceAppKey
from kolibri.plugins.app.utils import interface
from kolibri.plugins.app.utils import LAUNCH_INTENT


class FromSameDevicePermission(BasePermission):
    """
    Allow only users on the same device as the server
    """

    def has_permission(self, request, view):
        return request.META.get("REMOTE_ADDR") == "127.0.0.1"


APP_KEY_COOKIE_NAME = "app_key_cookie"


class FromAppViewPermission(BasePermission):
    def has_permission(self, request, view):
        return request.COOKIES.get(APP_KEY_COOKIE_NAME) == DeviceAppKey.get_app_key()


class AppCommandsViewset(ViewSet):

    permission_classes = (FromSameDevicePermission, FromAppViewPermission)

    if LAUNCH_INTENT in interface:

        @action(detail=False, methods=["post"])
        def launch_intent(self, request):
            filename = request.data.get("filename")
            message = request.data.get("message")
            if filename is None or message is None:
                raise APIException(
                    "filename and message parameters must be defined", code=412
                )
            interface.launch_intent(filename, message)
            return Response()


class InitializeAppView(APIView):
    permission_classes = (FromSameDevicePermission,)

    def get(self, request, token):
        app_key = DeviceAppKey.get_app_key()
        if app_key != token:
            raise PermissionDenied("You have provided an invalid token")
        redirect_url = request.GET.get("next", "/")
        # Copied and modified from https://github.com/django/django/blob/stable/1.11.x/django/views/i18n.py#L40
        if (redirect_url or not request.is_ajax()) and not is_safe_url(
            url=redirect_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            redirect_url = request.META.get("HTTP_REFERER")
            if redirect_url:
                redirect_url = urlunquote(redirect_url)  # HTTP_REFERER may be encoded.
            if not is_safe_url(
                url=redirect_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                redirect_url = "/"
        response = HttpResponseRedirect(redirect_url)
        response.set_cookie(APP_KEY_COOKIE_NAME, app_key)
        return response
