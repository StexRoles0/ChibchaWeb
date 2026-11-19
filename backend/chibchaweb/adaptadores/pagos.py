"""Adaptadores de los servicios de pago: verificación de tarjetas y procesador de cobros."""

from __future__ import annotations

from decimal import Decimal

import httpx

from chibchaweb.adaptadores._http import (
    cliente_por_omision,
    exigir_tarjeta,
    exigir_texto,
    exigir_url_https,
    vencimiento_aaaa_mm,
)
from chibchaweb.dominio.cuentas import MedioPago
from chibchaweb.dominio.errores import ReglaNegocioError
from chibchaweb.dominio.integraciones import PasarelaPago, ValidadorMedioPago


class AdaptadorValidadorTarjeta(ValidadorMedioPago):
    """Servicio externo de verificación: ``POST`` JSON → ``{"valida": true|false}``.

    El código de seguridad solo se envía si la tarjeta lo trae (antes de descartarse, RN-12) y nunca se registra.
    """

    def __init__(self, url_servicio: str, cliente_http: httpx.Client | None = None):
        self._url_servicio = exigir_url_https(url_servicio, "urlServicio")
        self._http = cliente_http or cliente_por_omision()

    @property
    def url_servicio(self) -> str:
        return self._url_servicio

    def verificar(self, medio: MedioPago) -> bool:
        tarjeta = exigir_tarjeta(medio)
        peticion = {
            "numero": tarjeta.numero,
            "vencimiento": vencimiento_aaaa_mm(tarjeta),
            "franquicia": tarjeta.franquicia.nombre,
        }
        if tarjeta.codigo_seguridad:
            peticion["codigoSeguridad"] = tarjeta.codigo_seguridad
        try:
            respuesta = self._http.post(self._url_servicio, json=peticion)
        except httpx.HTTPError:
            # sin traza encadenada: la petición lleva datos de la tarjeta
            raise ReglaNegocioError("El servicio de verificación de tarjetas no está disponible") from None
        if respuesta.status_code in (400, 402, 403, 422):
            return False
        if respuesta.status_code != 200:
            raise ReglaNegocioError("El servicio de verificación de tarjetas respondió con un error")
        return respuesta.json().get("valida") is True


class AdaptadorProcesadorPagos(PasarelaPago):
    """Procesador de las franquicias: ``POST`` JSON → ``{"aprobado": bool, "referencia": str}``.

    Devuelve la referencia o ``""`` si el cobro fue rechazado; las fallas de red o del servicio se propagan
    (``Suscripcion.cobrar`` las trata como cobro fallido).
    """

    def __init__(self, url_procesador: str, codigo_comercio: str, cliente_http: httpx.Client | None = None):
        self._url_procesador = exigir_url_https(url_procesador, "urlProcesador")
        self._codigo_comercio = exigir_texto(codigo_comercio, "codigoComercio")
        self._http = cliente_http or cliente_por_omision()

    @property
    def url_procesador(self) -> str:
        return self._url_procesador

    @property
    def codigo_comercio(self) -> str:
        return self._codigo_comercio

    def cobrar(self, medio: MedioPago, monto: Decimal) -> str:
        tarjeta = exigir_tarjeta(medio)
        peticion = {
            "codigoComercio": self._codigo_comercio,
            "numero": tarjeta.numero,
            "vencimiento": vencimiento_aaaa_mm(tarjeta),
            "franquicia": tarjeta.franquicia.nombre,
            "monto": str(monto),  # Decimal como texto (D-08)
            "moneda": "USD",
        }
        respuesta = self._http.post(self._url_procesador, json=peticion)
        if respuesta.status_code in (400, 402, 403, 422):  # rechazado por el procesador o la franquicia
            return ""
        respuesta.raise_for_status()
        datos = respuesta.json()
        return str(datos.get("referencia") or "") if datos.get("aprobado") is True else ""
