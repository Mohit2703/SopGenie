from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sop_rag.settings')

app = Celery('sop_rag')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Memory optimization settings
app.conf.update(
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks to free memory
    worker_prefetch_multiplier=1,   # Process one task at a time
    task_acks_late=True,            # Acknowledge task after completion
    task_reject_on_worker_lost=True,
    worker_max_memory_per_child=500000,  # 500MB max per worker (restart after)
)

app.autodiscover_tasks()
