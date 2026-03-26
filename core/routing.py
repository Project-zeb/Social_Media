from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # The URL the browser will connect to
   re_path(r'ws/disasters/$', consumers.DisasterConsumer.as_asgi()),
]