"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from api.consumers.websocket import WebsocketConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

django_asgi_app = get_asgi_application()
ws_asgi_app = URLRouter([path("ws", WebsocketConsumer.as_asgi())])

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": ws_asgi_app,
    }
)
