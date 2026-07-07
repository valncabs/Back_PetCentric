import re

_PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$")


def validate_password_strength(password: str) -> str:
    """Política de contraseña segura: mínimo 8 caracteres, una mayúscula,
    una minúscula, un número y un carácter especial."""
    if not _PASSWORD_PATTERN.match(password):
        raise ValueError(
            "La contraseña debe tener mínimo 8 caracteres, una mayúscula, "
            "una minúscula, un número y un carácter especial."
        )
    return password