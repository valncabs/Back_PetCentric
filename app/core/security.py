from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import bcrypt
from jose import jwt, JWTError
import hashlib
import secrets

from app.core.config import settings


# ---- Firma de tokens (HS256 por defecto, RS256 si hay llaves) ----

# Las llaves RSA se pueden configurar de dos formas:
#   - Inline: contenido PEM completo en JWT_PRIVATE_KEY / JWT_PUBLIC_KEY
#     (recomendado en PaaS como Render, donde no hay archivos persistentes).
#   - Por ruta: archivos PEM apuntados por JWT_PRIVATE_KEY_PATH /
#     JWT_PUBLIC_KEY_PATH (desarrollo local con la carpeta keys/).
# El contenido inline tiene prioridad sobre la ruta. Si no hay ninguna,
# se firma/verifica con SECRET_KEY (HS256).

def _load_key(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"No se pudo leer la llave JWT: {path} ({exc})")


def _has_private() -> bool:
    """True si hay llave privada configurada (contenido inline o ruta)."""
    return bool(settings.JWT_PRIVATE_KEY) or bool(settings.JWT_PRIVATE_KEY_PATH)


def _has_public() -> bool:
    """True si hay llave pública configurada (contenido inline o ruta)."""
    return bool(settings.JWT_PUBLIC_KEY) or bool(settings.JWT_PUBLIC_KEY_PATH)


def _signing_key() -> str:
    """Llave de FIRMA: privada en RS256, SECRET_KEY en HS256.

    Prioridad: contenido inline (JWT_PRIVATE_KEY) > ruta (JWT_PRIVATE_KEY_PATH)
    > SECRET_KEY.
    """
    if settings.JWT_PRIVATE_KEY:
        return settings.JWT_PRIVATE_KEY.strip()
    if settings.JWT_PRIVATE_KEY_PATH:
        return _load_key(settings.JWT_PRIVATE_KEY_PATH)
    return settings.SECRET_KEY


def _verify_key() -> str:
    """Llave de VERIFICACIÓN: pública en RS256, SECRET_KEY en HS256.

    Prioridad: contenido inline (JWT_PUBLIC_KEY) > ruta (JWT_PUBLIC_KEY_PATH)
    > SECRET_KEY.
    """
    if settings.JWT_PUBLIC_KEY:
        return settings.JWT_PUBLIC_KEY.strip()
    if settings.JWT_PUBLIC_KEY_PATH:
        return _load_key(settings.JWT_PUBLIC_KEY_PATH)
    return settings.SECRET_KEY


def _jwt_algorithm() -> str:
    """RS256 si se configuraron ambas llaves (inline o por ruta); si solo está
    una de cada lado, es un error de configuración que debe fallar de forma
    ruidosa, no en silencio. Sin llaves, fallback a settings.ALGORITHM."""
    has_private = _has_private()
    has_public = _has_public()
    if has_private != has_public:
        raise RuntimeError(
            "JWT: se debe definir la llave privada y la pública juntas "
            "(JWT_PRIVATE_KEY + JWT_PUBLIC_KEY, o JWT_PRIVATE_KEY_PATH + "
            "JWT_PUBLIC_KEY_PATH)."
        )
    if has_private:
        return "RS256"
    return settings.ALGORITHM or "HS256"


def hash_password(password: str) -> str:
    """Hashea con bcrypt directo (passlib está descontinuado).

    La validación de longitud (<= 72 bytes) se aplica en el esquema, no aquí:
    bcrypt trunca en silencio a 72 bytes y un truncado silencioso permitiría
    que dos contraseñas distintas que comparten los primeros 72 bytes colisionen.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, _signing_key(), algorithm=_jwt_algorithm())


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _verify_key(), algorithms=[_jwt_algorithm()])
        return payload
    except JWTError:
        raise ValueError("Token inválido o expirado")

def generate_opaque_token() -> tuple[str, str]:
    """Genera un token aleatorio seguro para enviar por correo (verificación
    de email / reset de contraseña) y su hash SHA-256 para persistir en BD.
    El valor crudo NUNCA se guarda en la base de datos."""
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, token_hash


def hash_opaque_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()