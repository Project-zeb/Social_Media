from django.utils import timezone
from core.models import DisasterEvent

def apply_global_decay():
    """
    Reduces the truth_score of all active events in the database.
    Run this once an hour to keep the data 'fresh'.
    """
    active_events = DisasterEvent.objects.filter(truth_score__gt=0.5)
    
    for event in active_events:
        # Reduce score by 10%
        event.truth_score = event.truth_score * 0.90
        
        # If score is now tiny, we can 'close' the event
        if event.truth_score < 1.0:
            event.is_active = False # You might need to add this field to models.py
            
        event.save()