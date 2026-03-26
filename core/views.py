from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.utils import timezone
from .models import DisasterEvent
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def dashboard(request, segment=None):
    """
    Unified Command Dashboard with AI-Capping and Strict Segment Segregation.
    """
    time_threshold = timezone.now() - timezone.timedelta(hours=24)
    flagged_count = DisasterEvent.objects.filter(status='FLAGGED').count()

    # 1. STRICT SEGMENT FILTERING LOGIC
    # These match the <str:segment> tokens in your urls.py
    if segment == 'VERIFIED':
        # SUPREME AUTHENTICATION: Strictly Human-Vetted (Tier 3)
        raw_alerts = DisasterEvent.objects.prefetch_related('posts').filter(
            status='VERIFIED', 
            intel_tier=3
        )
    elif segment == 'HIGH_PRIORITY':
        # AI-VERIFIED: Strictly Machine-Vetted (Tier 2)
        raw_alerts = DisasterEvent.objects.prefetch_related('posts').filter(
            status='HIGH_PRIORITY',
            intel_tier=2
        )
    elif segment == 'FLAGGED':
        # AI-FLAGGED: Items rejected or quarantined by the model (Tier 1)
        raw_alerts = DisasterEvent.objects.prefetch_related('posts').filter(
            status='FLAGGED'
        )
    elif segment == 'PENDING':
        # PENDING: Raw reports or those reset by Admin (Tier 1)
        raw_alerts = DisasterEvent.objects.prefetch_related('posts').filter(
            status='PENDING'
        )
    elif segment == 'FAKE':
        # FAKE: Reports dismissed as malicious
        raw_alerts = DisasterEvent.objects.prefetch_related('posts').filter(
            status='FAKE'
        )
    else:
        # DEFAULT LIVE FEED (Public): Show high-confidence AI and Official recent alerts
        raw_alerts = DisasterEvent.objects.prefetch_related('posts').filter(
            updated_at__gt=time_threshold,
            status__in=['HIGH_PRIORITY', 'VERIFIED']
        ).exclude(status='FAKE')
    
    # 2. TEMPORAL DECAY & THE 99% AI-CAP
    processed_alerts = []
    for alert in raw_alerts:
        time_diff = timezone.now() - alert.updated_at
        hours_passed = time_diff.total_seconds() / 3600
        
        # Exponential decay: 8% drop per hour (0.92 multiplier)
        decayed_score = alert.truth_score * (0.92 ** hours_passed)
        
        if alert.intel_tier < 3:
            # AI capped at 99.0% to prioritize human verification
            alert.display_score = min(round(decayed_score, 1), 99.0)
        else:
            # Admin Verified (Tier 3) shows true decay from 100%
            alert.display_score = round(decayed_score, 1)

        # 3. VISIBILITY CHECK
        # Management segments show everything; Live feed hides 'dead' reports
        if segment or alert.display_score > 0.1:
            processed_alerts.append(alert)

    # Sort by score (Highest first)
    processed_alerts.sort(key=lambda x: x.display_score, reverse=True)

    return render(request, 'core/dashboard.html', {
        'alerts': processed_alerts,
        'alert_count': len(processed_alerts),
        'flagged_count': flagged_count,
        'current_segment': segment or 'LIVE'
    })

def event_detail(request, event_id):
    """
    Detailed Intel View for a specific disaster.
    """
    event = get_object_or_404(DisasterEvent.objects.prefetch_related('posts'), id=event_id)
    flagged_count = DisasterEvent.objects.filter(status='FLAGGED').count()
    return render(request, 'core/event_detail.html', {
        'event': event,
        'flagged_count': flagged_count
    })

@login_required
def update_event_status(request, event_id, new_status):
    """
    Supreme Admin Authority: Handles transitions between Tier 1, 2, and 3.
    """
    event = get_object_or_404(DisasterEvent, id=event_id)
    event.status = new_status
    
    if new_status == 'VERIFIED':
        event.intel_tier = 3             # Official Human Authentication
        event.verified_by = request.user
        event.truth_score = 100.0        # Force max confidence
        msg = f"🛡️ OFFICIAL: Incident in {event.district} verified by {request.user.username}."
        
    elif new_status == 'FAKE':
        event.intel_tier = 0             # Dismissal
        event.truth_score = 0.0
        msg = f"🚫 DISMISSED: Incident in {event.district} marked as Fake."
        
    elif new_status == 'PENDING':
        event.intel_tier = 1             # Reset to Raw State
        event.truth_score = 25.0 
        msg = f"⏳ RESET: Incident in {event.district} moved to Pending Queue."
        
    else:
        # Manual adjustment for AI Priority levels
        event.intel_tier = 2 if new_status == 'HIGH_PRIORITY' else 1
        msg = f"🔄 STATUS: Updated to {new_status}."
        
    event.save()
    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

def download_report_pdf(request, event_id):
    """
    Generates a PDF report for the incident.
    """
    from .utils.pdf_generator import generate_incident_pdf 
    incident = get_object_or_404(DisasterEvent, id=event_id)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Report_{incident.id}.pdf"'
    return generate_incident_pdf(response, incident)

@login_required
def verify_event(request, event_id):
    """Legacy bridge for old URL tags"""
    return update_event_status(request, event_id, 'VERIFIED')

def review_queue(request):
    """Bridge for the navbar badge link"""
    return dashboard(request, segment='FLAGGED')