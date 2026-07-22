from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str
    APP_ENV: str = "development"

    # Base de datos
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    # Reset de contraseña
    PASSWORD_RESET_EXPIRE_MINUTES: int

    # Cooldown para reenviar verificación
    RESEND_VERIFICATION_COOLDOWN_SECONDS: int

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # Mailtrap
    MAILTRAP_HOST: str
    MAILTRAP_PORT: int
    MAILTRAP_USERNAME: str
    MAILTRAP_PASSWORD: str
    MAILTRAP_SENDER_EMAIL: str
    MAILTRAP_SENDER_NAME: str

    # Frontend
    FRONTEND_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()