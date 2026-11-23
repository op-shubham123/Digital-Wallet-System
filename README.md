# FlowPay — Digital Wallet & Payment Transaction System

A **full-stack portfolio project** built with **React, FastAPI, SQLAlchemy, MySQL (or SQLite for local demo), JWT authentication, and atomic wallet transfers**.

> **Important:** This is an educational demonstration with **simulated money only**. It is not a real payment processor or a production-ready financial application.

## Features

- Register and sign in with hashed passwords and JWT access tokens.
- Every new account receives **₹1,000 in clearly labeled simulated credits**.
- View wallet balance, total sent, total received, and recent transactions.
- Transfer credits to registered users by email.
- **ACID transactions**: sender debit, recipient credit, and transfer record commit together or roll back together.
- **Concurrency-safe conditional debit** prevents negative balances under concurrent requests.
- **Idempotency keys** prevent double charges on retries; duplicate keys with changed details return HTTP 409.
- Responsive dashboard, activity history, form validation, and error/success messages.
- Interactive API documentation at `/docs`.

## Stack

| Layer | Technologies |
|---|---|
| Frontend | React 18, Vite, CSS, Lucide icons |
| Backend | Python 3.10+, FastAPI, Pydantic, SQLAlchemy |
| Authentication | JWT (PyJWT), Argon2 password hashing |
| Database | MySQL 8+ via PyMySQL; SQLite for zero-setup development |
| Testing | Pytest, FastAPI TestClient |

## Quick start — Windows / VS Code

### 1. Backend

```powershell
cd backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

For local development the default `.env` uses SQLite, so no database server is needed. Change `JWT_SECRET` to a long random value. Then:

```powershell
uvicorn app.main:app --reload
```

API: http://localhost:8000  ·  Swagger docs: http://localhost:8000/docs

### 2. Frontend (second terminal)

Install Node.js 20+ and npm, then:

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open **http://localhost:5173**. Register two different users (e.g. `alice@example.com`, `bob@example.com`), sign in as Alice, and send Bob some demo credits. Sign in as Bob to see the received transfer.

## Optional: MySQL setup

Run in MySQL as an administrator (choose your own strong password):

```sql
CREATE DATABASE digital_wallet CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'wallet_user'@'localhost' IDENTIFIED BY 'replace_with_strong_password';
GRANT ALL PRIVILEGES ON digital_wallet.* TO 'wallet_user'@'localhost';
```

Update `backend/.env`:

```env
DATABASE_URL=mysql+pymysql://wallet_user:replace_with_strong_password@localhost:3306/digital_wallet
JWT_SECRET=replace-with-a-long-random-secret
ACCESS_TOKEN_MINUTES=60
CORS_ORIGINS=http://localhost:5173
```

Restart the backend. Tables are automatically created on startup. For real deployments, replace automatic schema creation with migration tooling (e.g. Alembic).

## Run tests

From `backend` with the virtual environment active:

```powershell
python -m pytest -q
```

Tests cover registration, login, duplicate emails, transfers, idempotency, insufficient funds, self-transfers, and authentication. The test database is isolated in `backend/test_wallet.db` and ignored by Git.

## API endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/health` | API health and demo mode |
| POST | `/auth/register` | Create account and demo wallet |
| POST | `/auth/login` | Get access token |
| GET | `/me` | Current user and balance |
| GET | `/transfers` | Last 100 sent/received transfers |
| POST | `/transfers` | Transfer simulated credits |

Sample request (authenticate with Bearer token):

```json
{
  "recipient_email": "bob@example.com",
  "amount": "125.50",
  "idempotency_key": "my-unique-transfer-0001"
}
```

## Transfer consistency design

All balances are stored as **integer paise**, avoiding floating-point rounding. Each transfer is performed within one database transaction:

1. Validate recipient and amount.
2. Atomically debit sender only if the available balance is sufficient (`UPDATE ... WHERE balance_cents >= amount`).
3. Check the sender's idempotency key; return a previous result or reject changed details.
4. Credit recipient and insert the transfer record.
5. Commit all changes together. Database errors roll back the entire operation.

The database enforces a unique `(sender_id, idempotency_key)` constraint. A failed insert cannot leave a partial debit or credit. SQLite may report database busy under concurrent writes; retry with the same idempotency key. MySQL/InnoDB is recommended for heavier concurrent testing.

## Folder structure

```text
digital-wallet-system/
├── backend/
│   ├── app/
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── security.py
│   ├── tests/test_api.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/App.jsx
│   ├── src/main.jsx
│   ├── src/styles.css
│   ├── index.html
│   ├── package.json
│   └── .env.example
├── .gitignore
└── README.md
```

## Security and production limitations

- Demo only; **no real payment gateway, KYC, bank connectivity, or real deposits**.
- Do not use real credentials or upload `.env` files to GitHub.
- JWT is stored in browser `sessionStorage` for simplicity. Production apps should consider hardened cookie/session handling and CSRF protections.
- Add rate limiting, email verification, audit logs, monitoring, security headers, migrations, operational backups, and proper secret management before any production deployment.
- API is intended for trusted local development; run behind HTTPS and a reverse proxy in a deployment.
- A transaction ledger, reconciliation, and stronger monetary controls would be needed for real financial systems.

## GitHub upload

```bash
git init
git add .
git commit -m "Build full-stack simulated digital wallet"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/digital-wallet-system.git
git push -u origin main
```

## Resume bullets (only after you have run and verified the project)

- Built a full-stack simulated digital wallet using **React, FastAPI, MySQL, and JWT authentication**, supporting peer-to-peer transfers and transaction history.
- Implemented **atomic balance updates, rollback handling, and idempotent requests** to prevent partial transfers, negative balances, and duplicate debits.

**License:** MIT — see `LICENSE`.
