import re

_PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$")
_BCRYPT_MAX_BYTES = 72


def validate_password_strength(password: str) -> str:
    """Política de contraseña segura: mínimo 8 caracteres, una mayúscula,
    una minúscula, un número y un carácter especial. Además rechaza contraseñas
    de más de 72 bytes (límite de bcrypt) para evitar el truncado silencioso,
    que haría colisionar contraseñas distintas con los mismos 72 primeros bytes."""
    if len(password.encode("utf-8")) > _BCRYPT_MAX_BYTES:
        raise ValueError(
            "La contraseña no puede superar los 72 bytes (máximo de bcrypt)."
        )
    if not _PASSWORD_PATTERN.match(password):
        raise ValueError(
            "La contraseña debe tener mínimo 8 caracteres, una mayúscula, "
            "una minúscula, un número y un carácter especial."
        )
    return password