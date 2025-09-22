# celery_worker.py
import os
from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery = Celery("worker", broker=redis_url, backend=redis_url)

@celery.task
def save_message_to_db(msg):
    # Implement DB save here (SQLAlchemy/whatever)
    print("Saving message to DB:", msg)
