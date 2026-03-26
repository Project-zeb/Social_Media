from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # This 'includes' all the paths you just defined in core/urls.py
    path('', include('core.urls')), 
]