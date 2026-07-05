"""Pydantic request/response schemas."""
import re

from pydantic import BaseModel, EmailStr, Field, field_validator

# Simple international/Iranian phone validation: digits, optional +, 10-15 length.
PHONE_RE = re.compile(r"^\+?\d{10,15}$")


def _normalize_phone(value: str) -> str:
    value = value.strip().replace(" ", "").replace("-", "")
    
    if value.startswith("09"):
        value = "+98" + value[1:]

    elif value.startswith("989"):
        value = "+" + value
        
    elif value.startswith("9"):
        value = "+98" + value
        
    if not PHONE_RE.match(value):
        raise ValueError("Invalid phone number. Use 10-15 digits, optional leading +.")
    return value


# ---------- Registration ----------
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    phone: str = Field(..., examples=["+989123456789"])
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def username_alnum(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[A-Za-z0-9_.]+$", v):
            raise ValueError("Username may contain only letters, digits, '_' and '.'")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _normalize_phone(v)


class VerifyOTPRequest(BaseModel):
    phone: str
    code: str = Field(..., min_length=4, max_length=8)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _normalize_phone(v)


class ResendOTPRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _normalize_phone(v)


# ---------- Login ----------
class LoginPhoneRequest(BaseModel):
    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _normalize_phone(v)


class LoginUsernameRequest(BaseModel):
    username: str
    password: str


# ---------- Responses ----------
class MessageResponse(BaseModel):
    message: str
    # In real life NEVER return the OTP. Returned here only for easy testing/demo.
    debug_otp: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ---------- Profile ----------
class UpdateProfileRequest(BaseModel):
    """All fields optional: only the ones provided get updated (partial update)."""
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=500)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


# ---------- Admin ----------
class BanRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    # Ban duration in minutes. Omit / null / 0 => permanent ban.
    minutes: int | None = Field(default=None, ge=0)


class UserResponse(BaseModel):
    id: int
    username: str
    phone: str
    email: EmailStr | None = None
    full_name: str | None = None
    address: str | None = None
    is_active: bool
    is_phone_verified: bool
    is_admin: bool = False

    model_config = {"from_attributes": True}
