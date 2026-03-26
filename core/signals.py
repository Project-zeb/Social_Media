from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DisasterEvent

@receiver(post_save, sender=DisasterEvent)
def trigger_critical_alert(sender, instance, created, **kwargs):
    """
    This function runs automatically EVERY time a DisasterEvent is saved or updated.
    """
    # 1. Threshold Check: If score is 20+ and still marked as PENDING
    if instance.truth_score >= 20.0 and instance.status == 'PENDING':
        
        # 2. Visual Alert for the Console (The "Shout")
        print("\n" + "!"*60)
        print(f"🚨 [SYSTEM ALERT]: CRITICAL {instance.event_type} DETECTED!")
        print(f"📍 LOCATION: {instance.district.upper()}")
        print(f"📡 CONFIDENCE: {instance.truth_score}%")
        print("🛠️ ACTION: PROMOTING TO 'VERIFIED' STATUS AUTOMATICALLY.")
        print("!"*60 + "\n")
        
        # 3. Database Action: Auto-verify the event
        # We use .update() here to avoid triggering this signal again in an infinite loop
        DisasterEvent.objects.filter(id=instance.id).update(status='VERIFIED')

    # 4. Cleanup Logic: If decay makes the score drop too low
    elif instance.truth_score < 5.0 and instance.status == 'VERIFIED':
        DisasterEvent.objects.filter(id=instance.id).update(status='PENDING')