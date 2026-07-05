"""Authentication routes.

Flow map:
  register -> verify-otp                         (creates the user)
  login/phone | login/username | token (form)    (returns access + refresh)
  refresh                                         (rotate: new access + refresh)
  logout                                          (revoke a refresh token)
  me (GET)                                        (read profile)
  me (PATCH)                                      (edit profile: email/name/address)
  change-password                                 (revokes all sessions)
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.request_info import client_meta
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginPhoneRequest,
    LoginUsernameRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResendOTPRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
    VerifyOTPRequest,
)
from app.services import bans as ban_service
from app.services import otp as otp_service
from app.services import tokens as token_service

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


# ---------- helpers ----------
def _ban_detail(ban: dict) -> dict:
    """Shape the ban record shown to a blocked user in the 403 response."""
    return {
        "error": "account_banned",
        "reason": ban.get("reason", "Your account has been banned."),
        "banned_at": ban.get("banned_at"),
        "until": ban.get("until"),  # None => permanent
        "expires_in_seconds": ban.get("expires_in"),
    }


def enforce_not_banned(user_id: int) -> None:
    """Raise 403 with the ban reason if the user is currently banned."""
    ban = ban_service.get_ban(user_id)
    if ban:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=_ban_detail(ban))


def _issue_tokens(user: User, request: Request) -> TokenResponse:
    """Create a fresh access + refresh token pair and register the refresh jti
    together with the client's session metadata (IP, browser, device, time)."""
    
    token_service.enforce_max_sessions(user.id, max_sessions=settings.max_session)
    
    access = create_access_token(user.id, extra={"username": user.username})
    refresh, jti = create_refresh_token(user.id)
    token_service.store_refresh(user.id, jti, client_meta(request))
    return TokenResponse(access_token=access, refresh_token=refresh)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    payload = decode_token(token)
    if not payload or payload.get("type") != ACCESS_TOKEN_TYPE or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found/inactive")
    enforce_not_banned(user.id)
    return user


# ---------- registration ----------
@router.post("/register", response_model=MessageResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(
        select(User).where(
            or_(User.username == data.username, User.phone == data.phone)
        )
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username or phone already registered")

    remaining = otp_service.is_on_cooldown(data.phone)
    if remaining:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"Please wait {remaining}s before requesting another OTP")

    code = otp_service.store_pending_registration(
        data.username, data.phone, hash_password(data.password)
    )
    # TODO: send `code` via SMS provider. For demo we return it as debug_otp.
    print(f"[OTP] phone={data.phone} code={code}")
    return MessageResponse(
        message="OTP sent. Verify it to complete registration.",
        debug_otp=code if settings.debug else None,
    )


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(data: VerifyOTPRequest, request: Request, db: Session = Depends(get_db)):
    pending = otp_service.get_pending_registration(data.phone)
    if not pending:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "No pending registration. Please register again.")

    ok, msg = otp_service.verify_code(data.phone, data.code)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)

    if db.scalar(select(User).where(
        or_(User.username == pending["username"], User.phone == pending["phone"]))
    ):
        otp_service.clear_pending(data.phone)
        raise HTTPException(status.HTTP_409_CONFLICT, "User already exists")

    user = User(
        username=pending["username"],
        phone=pending["phone"],
        hashed_password=pending["hashed_password"],
        is_phone_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    otp_service.clear_pending(data.phone)

    return _issue_tokens(user, request)


@router.post("/resend-otp", response_model=MessageResponse)
def resend_otp(data: ResendOTPRequest):
    if not otp_service.get_pending_registration(data.phone):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No pending registration")
    remaining = otp_service.is_on_cooldown(data.phone)
    if remaining:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"Please wait {remaining}s before resending")
    code = otp_service.regenerate_code(data.phone)
    print(f"[OTP-RESEND] phone={data.phone} code={code}")
    return MessageResponse(message="OTP resent.",
                           debug_otp=code if settings.debug else None)


# ---------- login ----------
@router.post("/login/phone", response_model=TokenResponse)
def login_phone(data: LoginPhoneRequest, request: Request, db: Session = Depends(get_db)):
    
    remaining = otp_service.is_on_cooldown(data.phone)
    if remaining:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"Please wait {remaining}s before resending")  
    otp_service.set_on_cooldown(data.phone)
    
    user = db.scalar(select(User).where(User.phone == data.phone))
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid phone or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    enforce_not_banned(user.id)
    return _issue_tokens(user, request)


@router.post("/login/username", response_model=TokenResponse)
def login_username(data: LoginUsernameRequest, request: Request, db: Session = Depends(get_db)):
    
    phone = db.scalar(select(User.phone).where(User.username == data.username))
    remaining = otp_service.is_on_cooldown(phone)
    if remaining:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"Please wait {remaining}s before resending")  
    otp_service.set_on_cooldown(phone)
    
    user = db.scalar(select(User).where(User.username == data.username))
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    enforce_not_banned(user.id)
    return _issue_tokens(user, request)


@router.post("/token", response_model=TokenResponse)
def login_oauth_form(request: Request,form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db),):
    """OAuth2-compatible login used by the Swagger UI "Authorize" button.

    The `username` field may contain either the account username OR the phone.
    """
    identifier = form_data.username
    user = db.scalar(
        select(User).where(or_(User.username == identifier, User.phone == identifier))
    )
    
    if user and user.phone:
        remaining = otp_service.is_on_cooldown(user.phone)
        if remaining:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Please wait {remaining}s before resending"
            )
        otp_service.set_on_cooldown(user.phone)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    enforce_not_banned(user.id)
    return _issue_tokens(user, request)


# ---------- refresh / logout ----------
@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a NEW access + refresh pair (rotation)."""
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != REFRESH_TOKEN_TYPE:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    user_id, jti = payload.get("sub"), payload.get("jti")
    if not user_id or not jti or not token_service.is_valid(user_id, jti):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Refresh token revoked or expired")

    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found/inactive")
    enforce_not_banned(user.id)

    # rotate: invalidate old refresh, issue new pair (carry fresh session meta)
    access = create_access_token(user.id, extra={"username": user.username})
    new_refresh, new_jti = create_refresh_token(user.id)
    token_service.rotate(user.id, jti, new_jti, client_meta(request))
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout", response_model=MessageResponse)
def logout(data: LogoutRequest):
    """Revoke a single refresh token (log out this session)."""
    payload = decode_token(data.refresh_token)
    if payload and payload.get("sub") and payload.get("jti"):
        token_service.revoke(payload["sub"], payload["jti"])
    # Always return success so we don't leak which tokens exist.
    return MessageResponse(message="Logged out.")


# ---------- profile ----------
@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Partial update: only provided fields are changed."""
    updates = data.model_dump(exclude_unset=True)

    # If email is being set/changed, ensure it isn't taken by someone else.
    if "email" in updates and updates["email"] is not None:
        clash = db.scalar(
            select(User).where(
                User.email == updates["email"], User.id != current_user.id
            )
        )
        if clash:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")

    for field, value in updates.items():
        setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "New password must be different from the current one")

    current_user.hashed_password = hash_password(data.new_password)
    db.add(current_user)
    db.commit()

    # Security: invalidate every existing session after a password change.
    token_service.revoke_all(current_user.id)
    return MessageResponse(message="Password changed. Please log in again.")
