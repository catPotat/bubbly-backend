from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security import websocket

from chat.routing import websocket_urlpatterns
from .middleware.channels_token_auth import TokenAuthMiddlewareStack

application = ProtocolTypeRouter({
    # (http->django views is added by default)
    'websocket':
        # websocket.AllowedHostsOriginValidator(
            TokenAuthMiddlewareStack(
                URLRouter(
                    websocket_urlpatterns,
                )
            )
        # )
})