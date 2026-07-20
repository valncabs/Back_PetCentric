from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str
    APP_ENV: str = "development"

    # Base de datos
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 1440  # 24 horas
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Reset de contraseña
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # Cooldown para reenviar verificación
    RESEND_VERIFICATION_COOLDOWN_SECONDS: int = 60  

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # Mailtrap
    MAILTRAP_HOST: str = "sandbox.smtp.mailtrap.io"
    MAILTRAP_PORT: int = 2525
    MAILTRAP_USERNAME: str
    MAILTRAP_PASSWORD: str
    MAILTRAP_SENDER_EMAIL: str = "noreply@pet-centric.com"
    MAILTRAP_SENDER_NAME: str = "Pet-Centric"

    # Frontend
    FRONTEND_URL: str = "http://localhost:4200"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()