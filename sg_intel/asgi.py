import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# --- STEP 1: IMPORT YOUR NEW ROUTING ---
import core.routing 

# Set the settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sg_intel.settings')

# Initialize the standard Django ASGI application
django_asgi_app = get_asgi_application()

# This is the "Traffic Police" for your server
application = ProtocolTypeRouter({
    # 1. Standard Web traffic (Browsing the dashboard)
    "http": django_asgi_app,
    
    # 2. Real-time traffic (The WebSocket connection)
    "websocket": AuthMiddlewareStack(
        URLRouter(
            # --- STEP 2: PLUG IN THE DISASTER ROUTE ---
            core.routing.websocket_urlpatterns
        )
    ),
})