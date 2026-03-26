import os
from celery import Celery

# 1. Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sg_intel.settings')

# 2. Create the Celery app instance
# This 'app' is what Celery is looking for when you run the command!
app = Celery('sg_intel')

# 3. Load task modules from all registered Django apps.
app.config_from_object('django.conf:settings', namespace='CELERY')

# 4. Auto-discover tasks in your core/tasks.py
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')