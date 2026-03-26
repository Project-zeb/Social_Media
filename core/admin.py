from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.http import HttpResponse

# Import your new PDF utility
from .utils.pdf_generator import generate_incident_pdf
from .models import DisasterEvent, SocialPost

class SocialPostInline(admin.TabularInline):
    model = SocialPost
    extra = 0
    readonly_fields = ('user_handle', 'raw_text', 'posted_at')

@admin.register(DisasterEvent)
class DisasterEventAdmin(admin.ModelAdmin):
    # What columns to show in the list
    list_display = ('colored_status', 'intel_tier', 'event_type', 'district', 'truth_score', 'verified_by')
    list_filter = ('status', 'intel_tier', 'event_type', 'created_at')
    search_fields = ('district',)
    inlines = [SocialPostInline]
    
    # Ensure these fields are editable in the admin form
    fields = ('status', 'intel_tier', 'event_type', 'district', 'grid_lat', 'grid_lon', 'truth_score', 'summary', 'verified_by')
    
    actions = ['export_as_pdf']

    def save_model(self, request, obj, form, change):
        """
        SUPREME SYNC LOGIC: This ensures that manual Admin changes 
        actually update the tiering system correctly.
        """
        if obj.status == 'VERIFIED':
            obj.intel_tier = 3
            obj.truth_score = 100.0
            if not obj.verified_by:
                obj.verified_by = request.user
        elif obj.status == 'PENDING':
            obj.intel_tier = 1
            # We don't reset truth_score to 0 here to allow AI to re-evaluate
        elif obj.status == 'FAKE':
            obj.intel_tier = 0
            obj.truth_score = 0.0
            
        super().save_model(request, obj, form, change)

    @admin.action(description='📦 Download PDF Report')
    def export_as_pdf(self, request, queryset):
        incident = queryset.first()
        if not incident:
            self.message_user(request, "Please select at least one incident.", level='error')
            return
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="SurgeGuard_Report_{incident.district}.pdf"'
        return generate_incident_pdf(response, incident)

    def colored_status(self, obj):
        colors = {
            'VERIFIED': '#10b981', # Green
            'PENDING': '#f59e0b',  # Orange
            'FAKE': '#ef4444',     # Red
            'FLAGGED': '#6366f1',  # Indigo
        }
        color = colors.get(obj.status, '#94a3b8')
        
        return format_html(
            '<b style="color:{}; text-transform:uppercase;">{}</b>',
            color,
            obj.status
        )
    colored_status.short_description = 'Status'

    def weather_validation(self, obj):
        if obj.weather_score >= 10:
            return format_html('<span style="color:green;">✔ Weather Confirmed</span>')
        return mark_safe('<span style="color:gray;">✘ No Weather Match</span>')