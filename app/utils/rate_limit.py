import asyncio
import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Depends, Request

from app.core.exceptions import TooManyRequestsException


class InMemoryRateLimiter:
    """Limiter deslizante en memoria (ventana fija por timestamps).

    Válido para despliegues de una sola instancia. Si el backend escala a
    varias instancias, migrar esta clase a una implementación con Redis
    (p. ej. con INCR + EXPIRE) manteniendo la misma interfaz.
    """

    # A partir de este número de claves se hace barrido de claves expiradas
    # para evitar que el diccionario crezca sin límite.
    _CLEANUP_THRESHOLD = 10_000

    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, max_attempts: int, window_seconds: float) -> None:
        """Registra el intento y, si se supera el máximo en la ventana, lanza
        TooManyRequestsException con el header Retry-After."""
        now = time.monotonic()
        async with self._lock:
            self._prune_expired(now, window_seconds)
            bucket = self._buckets[key]
            while bucket and bucket[0] <= now - window_seconds:
                bucket.popleft()

            if len(bucket) >= max_attempts:
                retry_after = int(window_seconds - (now - bucket[0])) + 1
                raise TooManyRequestsException(
                    "Demasiados intentos. Inténtalo de nuevo más tarde.",
                    retry_after=retry_after,
                )

            bucket.append(now)

    def _prune_expired(self, now: float, window_seconds: float) -> None:
        if len(self._buckets) < self._CLEANUP_THRESHOLD:
            return
        cutoff = now - window_seconds
        expired = [
            key
            for key, bucket in self._buckets.items()
            if not bucket or bucket[-1] <= cutoff
        ]
        for key in expired:
            del self._buckets[key]


rate_limiter = InMemoryRateLimiter()


def client_ip(request: Request) -> str:
    """IP del cliente, respetando el header X-Forwarded-For cuando la app
    está detrás de un proxy (p. ej. Render/Uvicorn con proxy headers)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_ip(prefix: str, max_attempts: int, window_seconds: float) -> Callable:
    """Factory de dependencia FastAPI: limita por IP del cliente.

    Uso:
        @router.post("/login", dependencies=[Depends(rate_limit_ip("login", 10, 900))])
    """

    async def dependency(request: Request) -> None:
        await rate_limiter.check(
            f"{prefix}:ip:{client_ip(request)}", max_attempts, window_seconds
        )

    return dependency
