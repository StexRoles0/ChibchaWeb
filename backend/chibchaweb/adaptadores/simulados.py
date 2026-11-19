"""Implementaciones simuladas de las interfaces de integración (D-05, D-06, P-10).

Siguen las mismas reglas que los adaptadores reales y no llaman a ningún servicio externo. El contenedor las
usa cuando ``SIMULAR_EXTERNOS=true``.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path

from chibchaweb.adaptadores.legado import leer_exportaciones
from chibchaweb.dominio.cuentas import MedioPago
from chibchaweb.dominio.errores import AutorizacionFallidaError
from chibchaweb.dominio.integraciones import (
    FuenteLegada,
    IdentidadExterna,
    PasarelaPago,
    ProveedorAutenticacion,
    RegistradorDominio,
    ValidadorMedioPago,
)

DIRECTORIO_DATOS_LEGADOS = Path(__file__).resolve().parents[2] / "datos_legados"
_TERMINACION_RECHAZADA_POR_VALIDADOR = "0002"
_TERMINACION_RECHAZADA_POR_PASARELA = "0341"
_MARCA_DOMINIO_RECHAZADO = "rechazo"


def _numero(medio: MedioPago) -> str:
    return getattr(medio, "numero", "")


class ProveedorAutenticacionSimulado(ProveedorAutenticacion):
    """``dev:<correo>`` devuelve una identidad verificada con ``sub = "dev|<correo>"`` (D-05).

    ``dev-noverificado:<correo>`` devuelve la misma identidad con el correo sin verificar.
    """

    def autorizar(self, codigo: str) -> IdentidadExterna:
        prefijo, _, correo = (codigo or "").partition(":")
        correo = correo.strip()
        if prefijo not in ("dev", "dev-noverificado") or not correo:
            raise AutorizacionFallidaError("Código de autorización inválido")
        nombre = correo.split("@")[0].replace(".", " ").title()
        return IdentidadExterna(f"dev|{correo}", nombre, correo, prefijo == "dev")


class ValidadorMedioPagoSimulado(ValidadorMedioPago):
    """Rechaza las tarjetas cuyo número termina en ``0002`` (D-06)."""

    def verificar(self, medio: MedioPago) -> bool:
        return not _numero(medio).endswith(_TERMINACION_RECHAZADA_POR_VALIDADOR)


class PasarelaPagoSimulada(PasarelaPago):
    """Rechaza (referencia vacía) las tarjetas que terminan en ``0341``; si no, devuelve ``REF-<uuid8>`` (D-06)."""

    def cobrar(self, medio: MedioPago, monto: Decimal) -> str:
        if _numero(medio).endswith(_TERMINACION_RECHAZADA_POR_PASARELA):
            return ""
        return f"REF-{uuid.uuid4().hex[:8]}"


class RegistradorDominioSimulado(RegistradorDominio):
    """Falla (falla de red simulada) con los documentos de dominios que contienen ``rechazo`` (D-06)."""

    def enviar(self, documento: str) -> None:
        if _MARCA_DOMINIO_RECHAZADO in documento:
            raise ConnectionError("Falla de red simulada en el registrador")


class FuenteLegadaSimulada(FuenteLegada):
    """Lee ``backend/datos_legados/{clientes,hosting,pagos}.csv``, con filas válidas e inválidas (D-06)."""

    def __init__(self, directorio: Path | str = DIRECTORIO_DATOS_LEGADOS):
        self._directorio = Path(directorio)

    def leer_registros(self) -> list[str]:
        return leer_exportaciones(self._directorio)
