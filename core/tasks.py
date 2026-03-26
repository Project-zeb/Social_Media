import json
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .utils.processor import process_social_intel
from .models import DisasterEvent

@shared_task
def analyze_disaster_intel_task(text, user_handle, post_id):
    """
    ULTRA-NICE: Processes data AND broadcasts it to the Live Dashboard.
    """
    print(f"⚙️ [WORKER]: Analyzing post {post_id} from @{user_handle}...")
    
    # 1. Run the heavy NLP and Weather logic
    result = process_social_intel(text, user_handle, post_id)
    
    # 2. Find the event that was just updated (linked to this post)
    # This ensures we send the MOST recent truth score to the dashboard
    event = DisasterEvent.objects.filter(posts__post_id=post_id).first()

    if event:
        # 3. Get the WebSocket "Switchboard"
        channel_layer = get_channel_layer()

        # 4. "SHOUT" the update to the 'disaster_updates' group
        # This message travels through Dragonfly to your Dashboard
        async_to_sync(channel_layer.group_send)(
            "disaster_updates",
            {
                "type": "disaster_update", # Calls the method in consumers.py
                "data": {
                    "id": event.id,
                    "event_type": event.event_type,
                    "district": event.district,
                    "truth_score": round(event.truth_score, 1),
                    "status": event.status,
                    "summary": event.summary,
                    "lat": event.grid_lat,
                    "lon": event.grid_lon,
                }
            }
        )
        print(f"📡 [BROADCAST]: Sent real-time update for {event.district} via WebSockets.")
    
    return result