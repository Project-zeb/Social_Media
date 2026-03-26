import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DisasterConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # The 'Group' name for everyone watching the dashboard
        self.group_name = "disaster_updates"

        # Join the group (Radio Station)
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Accept the connection
        await self.accept()
        print(f"📡 [WEBSOCKET]: Client connected to {self.group_name}")

    async def disconnect(self, close_code):
        # Leave the group when they close the tab
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        print("📡 [WEBSOCKET]: Client disconnected.")

    # This handles the message SENT to the group (from the Celery worker)
    async def disaster_update(self, event):
        """
        Receives data from the Channel Layer and PUSHES it to the Browser.
        """
        # Data is sent as a JSON object
        await self.send(text_data=json.dumps(event['data']))