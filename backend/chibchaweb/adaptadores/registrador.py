"""Adaptador del registrador de dominios externo."""

from __future__ import annotations

import httpx

from chibchaweb.adaptadores._http import cliente_por_omision, exigir_url_https
from chibchaweb.dominio.integraciones import RegistradorDominio


class AdaptadorRegistradorDominio(RegistradorDominio):
    """Transmite el XML de la solicitud (``POST`` ``application/xml``). Falla si la red o el registrador fallan."""

    def __init__(self, url_registrador: str, cliente_http: httpx.Client | None = None):
        self._url_registrador = exigir_url_https(url_registrador, "urlRegistrador")
        self._http = cliente_http or cliente_por_omision()

    @property
    def url_registrador(self) -> str:
        return self._url_registrador

    def enviar(self, documento: str) -> None:
        respuesta = self._http.post(
            self._url_registrador,
            content=documento.encode("utf-8"),
            headers={"Content-Type": "application/xml; charset=utf-8"},
        )
        respuesta.raise_for_status()
