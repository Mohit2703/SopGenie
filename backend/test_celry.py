from celery import Celery
import os

# Test Celery connection
app = Celery('test')

# Try different Redis URLs
redis_urls = [
    'redis://localhost:6379/0',
    'redis://127.0.0.1:6379/0',
    'redis://localhost:6379',
    'redis://127.0.0.1:6379',
]

for url in redis_urls:
    try:
        app.conf.broker_url = url
        app.conf.result_backend = url
        
        # Test connection
        i = app.control.inspect()
        i.stats()
        print(f"✅ SUCCESS: Connected to Redis at {url}")
        break
    except Exception as e:
        print(f"❌ FAILED: {url} - {e}")
