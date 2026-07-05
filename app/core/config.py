"""Application settings loaded from environment / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "OTP Auth Service"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./otp_auth.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    max_session: int = 3

    # JWT
    secret_key: str = "CHANGE_ME_super_secret_key_please_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # OTP
    otp_length: int = 6
    otp_ttl_seconds: int = 120
    otp_resend_cooldown: int = 60
    otp_max_attempts: int = 5
    registration_ttl_seconds: int = 600

    # Object storage (ArvanCloud S3-compatible)
    s3_endpoint_url: str = "https://hot.ir-central1.arvanstorage.ir"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = ""
    # Region label. ArvanCloud SDK examples use "default".
    s3_region: str = "default"
    # boto3 addressing style: "virtual" (ArvanCloud default / forcePathStyle:false)
    # or "path". Switch to "path" only if your endpoint needs it.
    s3_addressing_style: str = "virtual"
    # If True, uploaded objects are made public-read and served via a permanent
    # direct URL. If False (default), the bucket stays private and downloads use
    # short-lived presigned URLs.
    s3_public_read: bool = False
    # Per-file upload limit (bytes). Default 200 MB.
    max_upload_bytes: int = 200 * 1024 * 1024
    # Total bucket quota (bytes) used to display usage. Default 5 GB.
    bucket_quota_bytes: int = 5 * 1024 * 1024 * 1024
    # Lifetime (seconds) of the presigned download links we hand out.
    download_url_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
