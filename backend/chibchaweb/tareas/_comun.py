"""Auxiliares de los management commands (D-09). Solo conocen servicios y el contenedor."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import date

from django.core.management.base import CommandError

from chibchaweb.servicio.errores import ContingenciaActivaError, ErrorDominio
from config.contenedor import contenedor


def fecha_iso(texto: str) -> date:
    """Argumento ``AAAA-MM-DD`` de ``argparse``."""
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{texto!r} no es una fecha AAAA-MM-DD") from None


def exigir_sin_pendientes() -> None:
    """RT04: mientras haya eventos pendientes en el respaldo la tarea no corre.

    Un cobro respaldado todavía no está en la BD; si la tarea corriera de nuevo, la suscripción seguiría vencida y se
    cobraría dos veces (y lo mismo con las comisiones y los cheques). Hay que sincronizar antes
    (``POST /contingencia/sincronizacion``).
    """
    pendientes = contenedor().servicio_contingencia.consultar_respaldo_pendiente()
    if pendientes:
        raise CommandError(
            f"Hay {len(pendientes)} eventos pendientes en el respaldo de contingencia; "
            "sincronícelos antes de ejecutar la tarea."
        )


def ejecutar[R](accion: Callable[[], R]) -> R:
    """Traduce los errores del servicio a ``CommandError`` (código de salida distinto de cero para el cron)."""
    try:
        return accion()
    except ContingenciaActivaError as exc:
        raise CommandError(f"Contingencia activa: {exc.mensaje}") from exc
    except ErrorDominio as exc:
        raise CommandError(exc.mensaje) from exc
