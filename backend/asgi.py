"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from api.consumers.websocket import WebsocketConsumer, TestWebsocketConsumer
from backend import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

routes = [
    re_path(r"^ws/stacking/(?P<chain_id>\w+)$", WebsocketConsumer.as_asgi()),
    re_path(
        r"^ws/trade/(?P<chain_id>\w+)/(?P<base>\w+)/(?P<quote>\w+)$",
        WebsocketConsumer.as_asgi(),
    ),
]

routes += (
    [re_path(r"^ws/test/stacking/(?P<chain_id>\w+)$", TestWebsocketConsumer.as_asgi())]
    if settings.DEBUG
    else []
)
routes += (
    [
        re_path(
            r"^ws/test/trade/(?P<chain_id>\w+)/(?P<base>\w+)/(?P<quote>\w+)$",
            TestWebsocketConsumer.as_asgi(),
        )
    ]
    if settings.DEBUG
    else []
)

django_asgi_app = get_asgi_application()
ws_asgi_app = URLRouter(routes)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": ws_asgi_app,
    }
)
