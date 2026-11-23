import os
os.environ['DATABASE_URL'] = 'sqlite:///./test_wallet.db'
os.environ['JWT_SECRET'] = 'test-secret-not-for-production'
import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)
def register(name, email):
    res = client.post('/auth/register', json={'name': name, 'email': email, 'password': 'StrongPass123!'})
    assert res.status_code == 201, res.text
    return {'Authorization': 'Bearer ' + res.json()['access_token']}

def test_registration_and_login():
    headers = register('Alice', 'alice@example.com')
    assert client.get('/me', headers=headers).json()['balance'] == '1000.00'
    assert client.post('/auth/login', json={'email':'alice@example.com','password':'wrong'}).status_code == 401
    assert client.post('/auth/register', json={'name':'Alice','email':'alice@example.com','password':'StrongPass123!'}).status_code == 409

def test_transfer_idempotency_and_rollback():
    alice = register('Alice', 'alice@example.com')
    bob = register('Bob', 'bob@example.com')
    payload = {'recipient_email': 'bob@example.com', 'amount': '125.50', 'idempotency_key': 'unique-transfer-001'}
    assert client.post('/transfers', headers=alice, json=payload).status_code == 201
    assert client.post('/transfers', headers=alice, json=payload).status_code == 201
    assert client.get('/me', headers=alice).json()['balance'] == '874.50'
    assert client.get('/me', headers=bob).json()['balance'] == '1125.50'
    assert len(client.get('/transfers', headers=alice).json()) == 1
    conflict = dict(payload, amount='12.00')
    assert client.post('/transfers', headers=alice, json=conflict).status_code == 409
    too_much = dict(payload, amount='999999.00', idempotency_key='unique-transfer-002')
    assert client.post('/transfers', headers=alice, json=too_much).status_code == 400
    assert client.get('/me', headers=alice).json()['balance'] == '874.50'

def test_validation_and_auth():
    alice = register('Alice', 'alice@example.com')
    assert client.get('/me').status_code in (401,403)
    assert client.post('/transfers', headers=alice, json={'recipient_email':'alice@example.com','amount':'1.00','idempotency_key':'self-transfer-001'}).status_code == 400
    assert client.post('/transfers', headers=alice, json={'recipient_email':'nobody@example.com','amount':'1.00','idempotency_key':'unknown-user-001'}).status_code == 404
