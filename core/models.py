from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class DisasterEvent(models.Model):
    TYPE_CHOICES = [
        ('FLOOD', 'Flood'),
        ('FIRE', 'Forest Fire'),
        ('STORM', 'Severe Storm/Rain'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending AI Filter'),
        ('HIGH_PRIORITY', 'High Priority (AI Pass)'),
        ('FLAGGED', 'Suspicious (AI Mismatch)'),
        ('VERIFIED', 'Verified by Officer'),
        ('FAKE', 'Fake / Dismissed'),
    ]

    event_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    district = models.CharField(max_length=100)
    grid_lat = models.FloatField(db_index=True)
    grid_lon = models.FloatField(db_index=True)
    total_votes = models.IntegerField(default=1) 
    weather_score = models.FloatField(default=0.0) 
    intel_tier = models.IntegerField(default=1, db_index=True) # Defaulted to 1
    
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='verified_disasters'
    )

    ai_triage_score = models.FloatField(default=0.0, db_index=True)
    truth_score = models.FloatField(default=0.0, db_index=True)
    summary = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['truth_score']),
            models.Index(fields=['ai_triage_score']),
            models.Index(fields=['intel_tier']),
            models.Index(fields=['grid_lat', 'grid_lon']),
        ]

    def save(self, *args, **kwargs):
        """
        Model-level protection to ensure status and tier stay in sync.
        """
        if self.status == 'VERIFIED':
            self.intel_tier = 3
        elif self.status == 'HIGH_PRIORITY':
            self.intel_tier = 2
        elif self.status in ['PENDING', 'FLAGGED']:
            self.intel_tier = 1
        elif self.status == 'FAKE':
            self.intel_tier = 0
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event_type} in {self.district} ({self.status})"

class SocialPost(models.Model):
    event = models.ForeignKey(DisasterEvent, on_delete=models.CASCADE, related_name='posts')
    raw_text = models.TextField()
    image_url = models.URLField(blank=True, null=True)
    user_handle = models.CharField(max_length=100)
    post_id = models.CharField(max_length=100, unique=True) 
    posted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Post by @{self.user_handle} for {self.event.district}"