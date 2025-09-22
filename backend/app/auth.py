from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from . import database, models, schemas, utils

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register")
def register(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == form.username).first():
        raise HTTPException(400, "User already exists")
    user = models.User(username=form.username, hashed_password=utils.hash_password(form.password))
    db.add(user)
    db.commit()
    return {"msg": "registered"}

@router.post("/token", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form.username).first()
    if not user or not utils.verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    token = utils.create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
