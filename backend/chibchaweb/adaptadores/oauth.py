"""Adaptador del proveedor OAuth 2.0 / OpenID Connect (D-05): intercambia el código y valida el ID token.

Usa ``httpx`` para el intercambio y ``joserfc`` (la biblioteca JOSE de authlib, que ``authlib.jose`` declara
sucesora) para validar el ID token; ``authlib.jose`` y ``authlib.integrations.httpx_client`` están en desuso.
"""

from __future__ import annotations

import httpx
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet

from chibchaweb.adaptadores._http import TIEMPO_ESPERA, exigir_texto, exigir_url_https
from chibchaweb.dominio.errores import AutorizacionFallidaError
from chibchaweb.dominio.integraciones import IdentidadExterna, ProveedorAutenticacion

_RUTA_DESCUBRIMIENTO = "/.well-known/openid-configuration"


class AdaptadorOAuth(ProveedorAutenticacion):
    """``ProveedorAutenticacion`` real (Google por defecto).

    ``secreto_aplicacion`` y ``uri_redireccion`` son configuración del cliente OAuth que el intercambio del
    código exige y que el modelo no lista. ``transporte`` solo se usa en pruebas (``httpx.MockTransport``).
    """

    def __init__(
        self,
        url_proveedor: str,
        id_aplicacion: str,
        secreto_aplicacion: str = "",
        uri_redireccion: str = "",
        transporte: httpx.BaseTransport | None = None,
    ):
        self._url_proveedor = exigir_url_https(url_proveedor, "urlProveedor")
        self._id_aplicacion = exigir_texto(id_aplicacion, "idAplicacion")
        self._secreto_aplicacion = exigir_texto(secreto_aplicacion, "secretoAplicacion")
        self._uri_redireccion = exigir_texto(uri_redireccion, "uriRedireccion")
        self._transporte = transporte
        self._configuracion: dict | None = None

    @property
    def url_proveedor(self) -> str:
        return self._url_proveedor

    @property
    def id_aplicacion(self) -> str:
        return self._id_aplicacion

    def autorizar(self, codigo: str) -> IdentidadExterna:
        """Cambia el código por los tokens, valida el ID token y construye la ``IdentidadExterna``."""
        if not (codigo or "").strip():
            raise AutorizacionFallidaError("Falta el código de autorización")
        try:
            configuracion = self._descubrir()
            token = self._intercambiar(configuracion, codigo.strip())
            claims = self._validar_id_token(configuracion, token["id_token"])
        except (httpx.HTTPError, JoseError, KeyError, ValueError) as exc:
            raise AutorizacionFallidaError("No se pudo verificar la identidad con el proveedor") from exc
        return IdentidadExterna(
            identificador_externo=str(claims["sub"]),
            nombre=str(claims.get("name") or ""),
            correo=str(claims.get("email") or ""),
            correo_verificado=claims.get("email_verified") is True,
        )

    # --- pasos ----------------------------------------------------------------------------------
    def _descubrir(self) -> dict:
        if self._configuracion is None:
            with httpx.Client(transport=self._transporte, timeout=TIEMPO_ESPERA) as http:
                respuesta = http.get(self._url_proveedor + _RUTA_DESCUBRIMIENTO)
                respuesta.raise_for_status()
                self._configuracion = self._verificar_configuracion(respuesta.json())
        return self._configuracion

    def _verificar_configuracion(self, configuracion: dict) -> dict:
        """El emisor debe ser el proveedor configurado y los endpoints deben ser HTTPS (OIDC Discovery §4.3)."""
        if str(configuracion.get("issuer", "")).rstrip("/") != self._url_proveedor:
            raise ValueError("El emisor del documento de descubrimiento no coincide con el proveedor")
        for clave in ("token_endpoint", "jwks_uri"):
            if not str(configuracion[clave]).lower().startswith("https://"):
                raise ValueError(f"{clave} debe ser HTTPS")
        return configuracion

    def _intercambiar(self, configuracion: dict, codigo: str) -> dict:
        """Intercambio del código (RFC 6749 §4.1.3) con el cliente confidencial de ChibchaWEB."""
        formulario = {
            "grant_type": "authorization_code",
            "code": codigo,
            "client_id": self._id_aplicacion,
            "client_secret": self._secreto_aplicacion,
        }
        formulario["redirect_uri"] = self._uri_redireccion
        with httpx.Client(transport=self._transporte, timeout=TIEMPO_ESPERA) as http:
            respuesta = http.post(configuracion["token_endpoint"], data=formulario)
            respuesta.raise_for_status()
            return respuesta.json()

    def _validar_id_token(self, configuracion: dict, id_token: str) -> dict:
        with httpx.Client(transport=self._transporte, timeout=TIEMPO_ESPERA) as http:
            respuesta = http.get(configuracion["jwks_uri"])
            respuesta.raise_for_status()
            claves = KeySet.import_key_set(respuesta.json())
        token = jwt.decode(id_token, claves, algorithms=["RS256"])
        registro = jwt.JWTClaimsRegistry(
            iss={"essential": True, "value": configuracion["issuer"]},
            aud={"essential": True, "value": self._id_aplicacion},
            exp={"essential": True},
            sub={"essential": True},
        )
        registro.validate(token.claims)
        return token.claims
