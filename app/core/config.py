from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str
    APP_ENV: str = "development"

    # Logging (DEBUG | INFO | WARNING | ERROR)
    LOG_LEVEL: str = "INFO"

    # Base de datos
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    # Algoritmo de firma: "HS256" (por defecto) o "RS256" si se definen las
    # llaves JWT_PRIVATE_KEY_PATH / JWT_PUBLIC_KEY_PATH (o su contenido en
    # JWT_PRIVATE_KEY / JWT_PUBLIC_KEY). RS256 es lo recomendado en producción:
    # firma asimétrica, la llave privada nunca se comparte.
    ALGORITHM: str = "HS256"
    JWT_PRIVATE_KEY_PATH: str = ""
    JWT_PUBLIC_KEY_PATH: str = ""
    # Contenido PEM inline (para PaaS tipo Render donde no hay archivos).
    # Tiene prioridad sobre las rutas *_PATH. Enviar sin envuelta de saltos
    # de línea finales; se hace strip al cargar.
    JWT_PRIVATE_KEY: str = ""
    JWT_PUBLIC_KEY: str = ""
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

    # Asistente IA (function-calling sobre herramientas de base de datos)
    # Llave de Groq y modelo usado para redactar la respuesta.
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    # Proxy REST de herramientas (mcpo): base URL y API key opcional.
    AI_TOOL_PROXY_URL: str = "http://127.0.0.1:8000"
    AI_TOOL_PROXY_KEY: str = ""

    # CORS: lista de orígenes permitidos separados por coma.
    # Si está vacío, se usa FRONTEND_URL como único origen.
    CORS_ALLOWED_ORIGINS: str = ""

    # Rate limiting (por IP): intentos permitidos y ventana en segundos.
    LOGIN_RATE_LIMIT_MAX: int = 10
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 900
    FORGOT_PASSWORD_RATE_LIMIT_MAX: int = 5
    FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS: int = 900
    RESEND_VERIFICATION_RATE_LIMIT_MAX: int = 3
    RESEND_VERIFICATION_RATE_LIMIT_WINDOW_SECONDS: int = 900

    # WebSocket: límite de tamaño de mensaje y cadencia del keepalive.
    WS_MAX_MESSAGE_BYTES: int = 4096
    WS_PING_INTERVAL_SECONDS: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()