import os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
hasher = PasswordHash.recommended()
bearer = HTTPBearer()
SECRET = os.getenv('JWT_SECRET', 'development-only-change-this-secret')
ALGORITHM = 'HS256'
def hash_password(value):
    return hasher.hash(value)
def verify_password(value, hashed):
    return hasher.verify(value, hashed)
def create_token(user_id):
    expiry = datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv('ACCESS_TOKEN_MINUTES', '60')))
    return jwt.encode({'sub': str(user_id), 'exp': expiry}, SECRET, algorithm=ALGORITHM)
def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=[ALGORITHM])
        user = db.get(User, int(payload['sub']))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        user = None
    if not user:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    return user
