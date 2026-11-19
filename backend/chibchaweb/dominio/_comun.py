"""Auxiliares privados del dominio: reloj con zona de Bogotá, validaciones y propiedades repetidas.

No forma parte del modelo; ningún otro paquete debe importarlo.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from chibchaweb.dominio.errores import ValidacionError

ZONA = ZoneInfo("America/Bogota")
CENTAVOS = Decimal("0.01")
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PATRON_TELEFONO = re.compile(r"^[0-9 ]{0,20}$")


def ahora() -> datetime:
    """Fecha-hora actual con la zona America/Bogota."""
    return datetime.now(ZONA)


def hoy() -> date:
    """Fecha actual en America/Bogota."""
    return ahora().date()


def redondear(monto: Decimal) -> Decimal:
    """Redondea a 2 decimales con ROUND_HALF_UP (RN-01)."""
    return monto.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def a_decimal(valor: Any, campo: str) -> Decimal:
    """Convierte a Decimal sin pasar por float."""
    if isinstance(valor, float):
        raise ValidacionError(campo, "Los montos no pueden ser float; use Decimal")
    try:
        return Decimal(str(valor)) if not isinstance(valor, Decimal) else valor
    except Exception as exc:  # decimal.InvalidOperation
        raise ValidacionError(campo, f"{campo} no es un número decimal válido") from exc


def texto_obligatorio(valor: Any, campo: str, maximo: int) -> str:
    """Devuelve el texto sin espacios externos; falla si está vacío o excede el máximo."""
    texto = (valor or "").strip() if isinstance(valor, str) or valor is None else str(valor).strip()
    if not texto:
        raise ValidacionError(campo, f"El campo {campo} es obligatorio")
    if len(texto) > maximo:
        raise ValidacionError(campo, f"El campo {campo} admite máximo {maximo} caracteres")
    return texto


def es_correo(valor: str | None) -> bool:
    return bool(valor) and len(valor) <= 120 and PATRON_CORREO.match(valor) is not None


def misma_entidad(a: Any, b: Any) -> bool:
    """Dos objetos del dominio son la misma entidad si son el mismo objeto o tienen el mismo id."""
    if a is b:
        return True
    if a is None or b is None or type(a) is not type(b):
        return False
    return a.id is not None and a.id == b.id


def propiedad_id() -> property:
    """Identity Field: getter y setter que solo permite asignar el id una vez (lo hace el repositorio)."""

    def obtener(self: Any) -> int | None:
        return self._id

    def asignar(self: Any, valor: int) -> None:
        if self._id is not None and self._id != valor:
            raise ValidacionError("id", "El id ya fue asignado y no se puede cambiar")
        if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
            raise ValidacionError("id", "El id debe ser un entero positivo")
        self._id = valor

    return property(obtener, asignar, doc="Identificador asignado por la base de datos (Identity Field).")
