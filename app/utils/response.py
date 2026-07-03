from typing import Any
from fastapi.responses import JSONResponse


def success_response(data: Any = None, message: str = "OK", status_code: int = 200) -> JSONResponse:
    """Envelope estándar de éxito: {success, message, data}."""
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "message": message, "data": data},
    )