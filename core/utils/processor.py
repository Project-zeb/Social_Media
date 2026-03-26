import re
from django.utils import timezone
from datetime import timedelta
from core.models import DisasterEvent, SocialPost
from .nlp_processor import extract_location, identify_disaster_type
from .geo_mapper import get_coords_from_district
from .weather_service import get_live_weather_score

# Trusted handles for North India / National agencies
OFFICIAL_HANDLES = ['ndrfhq', 'indiametdept', 'uppolice', 'delhipolice', 'sdm_up']
NEWS_HANDLES = ['ani', 'ndtv', 'timesofindia', 'republic', 'indianexpress']

def get_3_word_status(text, event_type):
    """
    Mini-NLP Engine: Maps raw text to a high-density status.
    """
    text = text.lower()
    
    # 1. Intensity Detection
    intensity = "Moderate"
    if any(word in text for word in ['critical', 'massive', 'extreme', 'emergency', 'help', 'danger']):
        intensity = "Critical"
    elif any(word in text for word in ['slight', 'minor', 'small']):
        intensity = "Minor"
    
    # 2. Trend Detection
    trend = "Active"
    if any(word in text for word in ['rising', 'increasing', 'more', 'spreading', 'heavy']):
        trend = "Escalating"
    elif any(word in text for word in ['subsiding', 'receding', 'decreasing', 'controlled']):
        trend = "Receding"

    return f"{intensity} {event_type.capitalize()}: {trend}"

def detect_regional_spread(current_event):
    """
    ULTRA-NICE: Spatial Intelligence logic to detect spreading disasters.
    """
    # Look for other events of the same type within the last 6 hours
    time_limit = timezone.now() - timedelta(hours=6)
    neighbors = DisasterEvent.objects.filter(
        event_type=current_event.event_type,
        truth_score__gt=10.0,
        updated_at__gte=time_limit
    ).exclude(id=current_event.id)

    for neighbor in neighbors:
        # Calculate grid distance (0.6 degrees is ~60-65km in North India)
        lat_diff = abs(current_event.grid_lat - neighbor.grid_lat)
        lon_diff = abs(current_event.grid_lon - neighbor.grid_lon)
        
        if lat_diff <= 0.6 and lon_diff <= 0.6:
            return f"⚠️ REGIONAL {current_event.event_type} CRISIS: Linked with {neighbor.district} sector."
    
    return "Localized Event"

def get_source_weight(user_handle):
    handle = str(user_handle).lower().strip()
    if handle in OFFICIAL_HANDLES:
        return 15.0
    elif handle in NEWS_HANDLES:
        return 7.0
    return 1.0

def extract_hashtags(text):
    return re.findall(r"#(\w+)", text.lower())

def generate_situational_summary(event):
    """
    Generates the final briefing using NLP, Spatial, and Verification data.
    """
    post_count = event.posts.count()
    latest_post = event.posts.first()
    latest_text = latest_post.raw_text if latest_post else ""
    
    # 1. Mini-NLP Status
    brief_status = get_3_word_status(latest_text, event.event_type)
    
    # 2. Regional Connectivity (Feature 2.3)
    regional_intel = detect_regional_spread(event)
    
    # 3. Final Verification Status
    status_label = "VERIFIED" if event.truth_score >= 20 else "PRELIMINARY"
    
    # Building the elite summary string
    summary = (
        f"{regional_intel} | INTEL: {brief_status}. "
        f"Verification: {status_label} ({post_count} sources). "
        f"Latest: '{latest_text[:60]}...'"
    )
    return summary

def process_social_intel(text, user_handle, post_id):
    # 1. Extraction
    location_name = extract_location(text)
    disaster_type = identify_disaster_type(text)
    
    if not location_name or not disaster_type:
        return "❌ Missing location or disaster type"

    # 2. Grid Mapping
    lat, lon = get_coords_from_district(location_name)
    if not lat:
        return f"❌ Location '{location_name}' not in North India grid"

    # 3. Source Credibility
    source_weight = get_source_weight(user_handle)

    # 4. Momentum Check (Hashtags)
    hashtags = extract_hashtags(text)
    hashtag_multiplier = 1.0
    if hashtags:
        half_hour_ago = timezone.now() - timedelta(minutes=30)
        for tag in hashtags:
            recent_uses = SocialPost.objects.filter(
                raw_text__icontains=f"#{tag}",
                posted_at__gte=half_hour_ago 
            ).values('user_handle').distinct().count()

            if recent_uses >= 5:
                hashtag_multiplier = 1.5
                break 

    # 5. Event Clustering
    time_threshold = timezone.now() - timedelta(hours=4)
    existing_event = DisasterEvent.objects.filter(
        event_type=disaster_type,
        grid_lat=lat,
        grid_lon=lon,
        updated_at__gte=time_threshold
    ).first()

    calculated_boost = source_weight * hashtag_multiplier

    if existing_event:
        existing_event.total_votes += 1
        existing_event.truth_score += calculated_boost
        event = existing_event
    else:
        w_score = get_live_weather_score(lat, lon, disaster_type)
        event = DisasterEvent.objects.create(
            event_type=disaster_type,
            district=location_name,
            grid_lat=lat,
            grid_lon=lon,
            weather_score=w_score,
            total_votes=1,
            truth_score=calculated_boost + w_score 
        )

    # 6. Documentation
    SocialPost.objects.create(
        event=event,
        raw_text=text,
        user_handle=user_handle,
        post_id=post_id
    )

    # 7. UPDATE INTEL & AUTO-VERIFY (The "Brain" of the system)
    # Generate situational summary incorporating regional detection
    event.summary = generate_situational_summary(event)

    # Automated Verification Logic
    if event.truth_score >= 20.0:
        event.status = 'VERIFIED'
    elif event.truth_score < 5.0:
        event.status = 'PENDING'
    
    event.save()
    
    return f"✅ Linked. Weight: {source_weight} | Multiplier: {hashtag_multiplier}x | Truth Score: {event.truth_score}"