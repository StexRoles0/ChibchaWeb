"""Reloj del servicio con la zona America/Bogota (el dominio no expone el suyo)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("America/Bogota")


def hoy() -> date:
    return datetime.now(ZONA).date()
