from datetime import datetime, timezone


def iso_datetime(value: datetime | None) -> str | None:
    """Serializa una fecha en formato ISO 8601 con zona horaria UTC.

    La BD guarda timestamps naive en UTC (columnas `timestamp without time
    zone`); sin marcar la zona, `new Date()` en el frontend los interpreta
    como hora local y la hora mostrada sería incorrecta.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
