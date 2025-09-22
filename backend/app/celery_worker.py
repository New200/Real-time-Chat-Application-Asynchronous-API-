import os
from celery import Celery
from sqlalchemy.orm import Session
from . import database, models

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery = Celery("worker", broker=redis_url, backend=redis_url)

@celery.task
def save_message(username, room, text):
    db: Session = database.SessionLocal()
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        msg = models.Message(user_id=user.id, room=room, text=text)
        db.add(msg)
        db.commit()
    db.close()
