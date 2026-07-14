import uuid
from pydantic import field_validator
from app.schemas.common import OrmModel


class LoginRequest(OrmModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v


class TokenResponse(OrmModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(OrmModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    email: str
    full_name: str
    is_active: bool


class RegisterRequest(OrmModel):
    workspace_name: str
    email: str
    password: str
    full_name: str

    @field_validator("email")
    @classmethod
    def normalise_register_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v
