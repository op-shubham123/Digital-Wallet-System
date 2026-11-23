from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field
class Register(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
class Login(BaseModel):
    email: EmailStr
    password: str
class TransferInput(BaseModel):
    recipient_email: EmailStr
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    idempotency_key: str = Field(min_length=8, max_length=100)
