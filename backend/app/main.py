import os
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update, or_
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import User, Wallet, Transfer
from .schemas import Register, Login, TransferInput
from .security import hash_password, verify_password, create_token, current_user

Base.metadata.create_all(bind=engine)
app = FastAPI(title='Digital Wallet API', version='1.0.0', description='Demo wallet: simulated funds only')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

def money(cents):
    return f'{Decimal(cents) / 100:.2f}'

def transfer_dict(t, me, db):
    other_id = t.recipient_id if t.sender_id == me else t.sender_id
    other = db.get(User, other_id)
    return {'id': t.id, 'type': 'sent' if t.sender_id == me else 'received', 'counterparty': other.name, 'email': other.email, 'amount': money(t.amount_cents), 'created_at': t.created_at.isoformat()}

@app.get('/health')
def health():
    return {'status': 'ok', 'mode': 'simulated-money'}

@app.post('/auth/register', status_code=201)
def register(body: Register, db: Session = Depends(get_db)):
    email = body.email.lower()
    user = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.flush()
        db.add(Wallet(user_id=user.id, balance_cents=100000))  # clearly labeled demo credit
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Email already registered')
    return {'access_token': create_token(user.id), 'token_type': 'bearer'}

@app.post('/auth/login')
def login(body: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid email or password')
    return {'access_token': create_token(user.id), 'token_type': 'bearer'}

@app.get('/me')
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id))
    return {'id': user.id, 'name': user.name, 'email': user.email, 'balance': money(wallet.balance_cents), 'currency': 'INR', 'demo': True}

@app.get('/transfers')
def transfers(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Transfer).where(or_(Transfer.sender_id == user.id, Transfer.recipient_id == user.id)).order_by(Transfer.id.desc()).limit(100)).all()
    return [transfer_dict(t, user.id, db) for t in items]

@app.post('/transfers', status_code=201)
def send(body: TransferInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cents = int(body.amount * 100)
    if cents <= 0:
        raise HTTPException(400, 'Amount must be positive')
    if cents > 100000000:
        raise HTTPException(400, 'Demo transfer limit is ₹10,00,000')
    recipient = db.scalar(select(User).where(User.email == body.recipient_email.lower()))
    if not recipient:
        raise HTTPException(404, 'Recipient not found')
    if recipient.id == user.id:
        raise HTTPException(400, 'Cannot transfer to yourself')
    try:
        # Conditional debit is atomic even under concurrent requests; prevents negative balances.
        debit = db.execute(update(Wallet).where(Wallet.user_id == user.id, Wallet.balance_cents >= cents).values(balance_cents=Wallet.balance_cents - cents))
        if debit.rowcount != 1:
            db.rollback()
            existing = db.scalar(select(Transfer).where(Transfer.sender_id == user.id, Transfer.idempotency_key == body.idempotency_key))
            if existing:
                if existing.recipient_id != recipient.id or existing.amount_cents != cents:
                    raise HTTPException(409, 'Idempotency key already used with different details')
                return transfer_dict(existing, user.id, db)
            raise HTTPException(400, 'Insufficient funds')
        # A unique (sender, key) constraint prevents duplicate transfers. On failure the debit rolls back.
        existing = db.scalar(select(Transfer).where(Transfer.sender_id == user.id, Transfer.idempotency_key == body.idempotency_key))
        if existing:
            db.rollback()
            if existing.recipient_id != recipient.id or existing.amount_cents != cents:
                raise HTTPException(409, 'Idempotency key already used with different details')
            return transfer_dict(existing, user.id, db)
        db.execute(update(Wallet).where(Wallet.user_id == recipient.id).values(balance_cents=Wallet.balance_cents + cents))
        transfer = Transfer(sender_id=user.id, recipient_id=recipient.id, amount_cents=cents, idempotency_key=body.idempotency_key)
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        return transfer_dict(transfer, user.id, db)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Transfer).where(Transfer.sender_id == user.id, Transfer.idempotency_key == body.idempotency_key))
        if existing:
            if existing.recipient_id != recipient.id or existing.amount_cents != cents:
                raise HTTPException(409, 'Idempotency key already used with different details')
            return transfer_dict(existing, user.id, db)
        raise HTTPException(409, 'Transfer conflict; retry')
    except OperationalError:
        db.rollback()
        raise HTTPException(503, 'Database busy; retry with same idempotency key')
