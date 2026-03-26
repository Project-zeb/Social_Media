from django.urls import path
from . import views

urlpatterns = [
    # 1. Main Feed (The Live Dashboard)
    path('', views.dashboard, name='dashboard'),
    
    # 2. Segmented Tabs (The Command Center)
    # This captures PENDING, FLAGGED, HIGH_PRIORITY, VERIFIED, or FAKE from the URL
    path('segment/<str:segment>/', views.dashboard, name='segment_filter'),
    
    # 3. Detailed Intel View
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    
    # 4. Supreme Power Command (The Verify/Fake/Reset Buttons)
    path('update-status/<int:event_id>/<str:new_status>/', views.update_event_status, name='update_status'),
    
    # 5. Legacy Bridge Paths
    path('review/', views.review_queue, name='review_queue'),
    path('verify/<int:event_id>/', views.verify_event, name='verify_event'),
    
    # 6. Official Reporting
    path('download-pdf/<int:event_id>/', views.download_report_pdf, name='download_report_pdf'),
]