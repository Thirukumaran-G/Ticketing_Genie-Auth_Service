from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str
    APP_URL: str 
    SERVICE_NAME: str
    LOG_LEVEL: str
    DEBUG: bool

    # Database
    DATABASE_URL: str 
    PORT: int

    # JWT
    SECRET_KEY: str                       
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # Password reset
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # SMTP
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str
    SMTP_USE_TLS: bool
    
    # middleware
    ALLOWED_ORIGINS: str
    TRUSTED_HOSTS: str
    
    

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters.")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string.")
        return v

    @property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def trusted_host_list(self) -> list[str]:
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True}


settings = Settings()  # type: ignore[call-arg]