import os
import requests
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from django.conf import settings

def generate_incident_pdf(response, incident):
    p = canvas.Canvas(response, pagesize=letter)
    
    # --- 1. Header & Dynamic Branding (Power Tiers) ---
    p.setFont("Helvetica-Bold", 18)
    
    # TIER 3: Admin Supreme Authority
    if incident.intel_tier == 3:
        p.setFillColor(colors.darkgreen)
        p.drawString(50, 770, "🛡️ SUPREME AUTHORITY INCIDENT REPORT")
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, 755, f"MANUALLY VETTED BY OFFICER: {incident.verified_by.username if incident.verified_by else 'ADMIN'}")
        p.setStrokeColor(colors.darkgreen)
    
    # TIER 2: AI Mathematical Verification
    elif incident.intel_tier == 2:
        p.setFillColor(colors.blue)
        p.drawString(50, 770, "🤖 AI-VALIDATED INTELLIGENCE REPORT")
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, 755, "VERIFIED VIA MULTIMODAL VECTOR ALIGNMENT (CLIP)")
        p.setStrokeColor(colors.blue)
        
    # TIER 1/0: Unverified/Flagged
    else:
        p.setFillColor(colors.red)
        p.drawString(50, 770, "⚠️ UNVERIFIED CITIZEN INTELLIGENCE")
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, 755, "PRELIMINARY DATA: AWAITING MANUAL TRIAGE")
        p.setStrokeColor(colors.red)

    p.line(50, 745, 550, 745)
    p.setFillColor(colors.black) # Reset to black for body text

    # --- 2. Incident Summary Box ---
    p.setFont("Helvetica-Bold", 12)
    p.setStrokeColor(colors.black)
    p.rect(50, 630, 250, 105, stroke=1, fill=0)
    
    p.drawString(60, 715, f"TYPE: {incident.event_type}")
    p.setFont("Helvetica", 11)
    p.drawString(60, 695, f"Location: {incident.district}")
    p.drawString(60, 675, f"Grid Coords: {incident.grid_lat}, {incident.grid_lon}")
    
    # Showing the Math Score
    p.setFont("Helvetica-Bold", 11)
    p.drawString(60, 655, f"AI Match Score: {incident.ai_triage_score:.2f}")
    p.setFont("Helvetica", 11)
    p.drawString(60, 640, f"System Status: {incident.get_status_display()}")

    # --- 3. OPTIMIZED STATIC MAP LAYER (Cached) ---
    map_filename = f"map_{incident.grid_lat}_{incident.grid_lon}.png"
    map_cache_dir = os.path.join(settings.BASE_DIR, 'media', 'map_cache')
    map_path = os.path.join(map_cache_dir, map_filename)
    
    try:
        if os.path.exists(map_path):
            map_img = ImageReader(map_path)
        else:
            map_url = f"https://static-maps.yandex.ru/1.x/?ll={incident.grid_lon},{incident.grid_lat}&z=10&l=map&size=300,300&pt={incident.grid_lon},{incident.grid_lat},pm2rdm"
            map_response = requests.get(map_url, timeout=5)
            if map_response.status_code == 200:
                os.makedirs(map_cache_dir, exist_ok=True)
                with open(map_path, 'wb') as f:
                    f.write(map_response.content)
                map_img = ImageReader(BytesIO(map_response.content))
            else:
                raise Exception("Map API error")

        p.drawImage(map_img, 310, 630, width=240, height=105)
        p.setFont("Helvetica-Oblique", 8)
        p.drawString(310, 615, "Figure 1: Grid Sector Satellite/Context View")
    except Exception:
        p.setFont("Helvetica-Oblique", 8)
        p.drawString(310, 630, "[Satellite View Temporarily Unavailable]")

    # --- 4. AI SITUATIONAL BRIEFING BOX ---
    p.setFillColor(colors.lightgrey)
    p.rect(50, 550, 500, 50, fill=1, stroke=0)
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(60, 585, "AI-GENERATED SITUATIONAL BRIEFING (TRANSLATED)")
    
    p.setFont("Helvetica-Oblique", 9)
    # The summary is generated via Helsinki-NLP in triage.py
    briefing = incident.summary if incident.summary else "Intelligence analysis in progress..."
    p.drawString(60, 565, briefing[:115]) 
    if len(briefing) > 115:
        p.drawString(60, 555, briefing[115:230])

    # --- 5. Social Media Evidence Table ---
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, 510, "Intelligence Source Logs (Multilingual Feed)")
    p.line(50, 505, 320, 505)

    y = 480
    p.setFont("Helvetica", 9)
    for post in incident.posts.all()[:12]:
        p.circle(55, y+3, 1.5, fill=1) 
        clean_text = post.raw_text.replace('\n', ' ')[:95]
        p.drawString(65, y, f"@{post.user_handle}: {clean_text}...")
        y -= 18
        if y < 80: break 

    # --- 6. Footer ---
    p.setFont("Helvetica-Oblique", 8)
    tier_text = f"Priority Tier: {incident.intel_tier}"
    footer_text = f"Generated: {incident.updated_at.strftime('%Y-%m-%d %H:%M')} | {tier_text} | SurgeGuard AI Security Protocol"
    p.drawCentredString(300, 40, footer_text)

    p.showPage()
    p.save()
    return response