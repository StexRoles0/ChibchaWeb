"""Auxiliares privados de los adaptadores HTTP."""

from __future__ import annotations

import httpx

from chibchaweb.dominio.cuentas import MedioPago, TarjetaCredito
from chibchaweb.dominio.errores import ReglaNegocioError, ValidacionError

TIEMPO_ESPERA = 10.0


def exigir_url_https(valor: str, campo: str) -> str:
    """Los servicios externos se consumen solo por HTTPS (rango de valores del modelo)."""
    url = (valor or "").strip().rstrip("/")
    if not url.lower().startswith("https://") or len(url) <= len("https://"):
        raise ValidacionError(campo, f"{campo} debe ser una URL HTTPS")
    return url


def exigir_texto(valor: str, campo: str) -> str:
    texto = (valor or "").strip()
    if not texto:
        raise ValidacionError(campo, f"{campo} es obligatorio")
    return texto


def cliente_por_omision() -> httpx.Client:
    return httpx.Client(timeout=TIEMPO_ESPERA)


def exigir_tarjeta(medio: MedioPago) -> TarjetaCredito:
    if not isinstance(medio, TarjetaCredito):
        raise ReglaNegocioError("Solo se admiten tarjetas de crédito")
    return medio


def vencimiento_aaaa_mm(tarjeta: TarjetaCredito) -> str:
    return tarjeta.vencimiento.strftime("%Y-%m")
