from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


def _validate_password_length(cls: type[BaseModel], password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be 72 bytes or fewer.")
    return password


class AdminRegistration(BaseModel):
    username: str
    password: str = Field(min_length=8)
    email: EmailStr
    admin_code: str

    _password_length = validator("password", allow_reuse=True)(
        _validate_password_length
    )


class AdminLogin(BaseModel):
    username: str
    password: str

    _password_length = validator("password", allow_reuse=True)(
        _validate_password_length
    )


class UserRegistration(BaseModel):
    username: str
    password: str = Field(min_length=8)
    email: EmailStr

    _password_length = validator("password", allow_reuse=True)(
        _validate_password_length
    )


class UserLogin(BaseModel):
    username: str
    password: str

    _password_length = validator("password", allow_reuse=True)(
        _validate_password_length
    )


class UserOut(BaseModel):
    username: str
    created_at: datetime
    email: EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
