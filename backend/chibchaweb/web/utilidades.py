"""Ayudas de la capa web: transacción por petición (D-10), sesión del usuario y flujo OAuth (arquitectura §7)."""

from __future__ import annotations

import functools
import hmac
import secrets
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.db import InterfaceError, OperationalError

from chibchaweb.servicio.dto import ResultadoAccesoDTO
from chibchaweb.servicio.errores import AutorizacionFallidaError
from chibchaweb.transaccion import transaccion

# Claves de la sesión de Django
CLAVE_ID = "id_usuario"
CLAVE_PENDIENTE = "identidad_pendiente"
CLAVE_ESTADO = "oauth_state"
_CLAVES_SESION = ("id_usuario", "tipo_usuario", "rol", "operaciones", "nombre", "correo")


def transaccional(funcion):
    """Envuelve el método de la vista en una transacción (``transaction.atomic()`` con cuenta de escrituras, D-33).

    Con la BD caída (RT04, D-30) cerrar la transacción también falla: Django intenta reconectar al salir del bloque y
    esa ``OperationalError`` taparía la excepción que de verdad importa, la ``ContingenciaActivaError`` que lanzó el
    mapeador cuando ya había respaldado el evento. Por eso, si el cierre falla por la conexión, se vuelve a lanzar la
    excepción original de la vista (si no hubo, la propia falla de la BD, que el manejador traduce a 503).
    """

    @functools.wraps(funcion)
    def envoltura(*args, **kwargs):
        original: Exception | None = None
        try:
            with transaccion():
                try:
                    return funcion(*args, **kwargs)
                except Exception as exc:
                    original = exc
                    raise
        except (OperationalError, InterfaceError):
            if original is None:
                raise
            raise original from None

    return envoltura


@dataclass(frozen=True)
class SesionUsuario:
    """Lo que la sesión sabe del usuario autenticado (no es una clase del modelo)."""

    id_usuario: int
    tipo_usuario: str
    rol: str | None
    operaciones: tuple[str, ...]
    nombre: str
    correo: str

    is_authenticated = True

    def permite(self, operacion: str) -> bool:
        return operacion in self.operaciones


def sesion_usuario(request) -> SesionUsuario:
    """Usuario autenticado de la petición (la autenticación por sesión lo deja en ``request.user``)."""
    return request.user


def valor_de_campo(detalle, clave: str) -> str:
    """Valor de ``"clave: valor"`` en los ``campos`` de un ``DetalleDTO``."""
    prefijo = f"{clave}: "
    return next(c[len(prefijo) :] for c in detalle.campos if c.startswith(prefijo))


def abrir_sesion(request, resultado: ResultadoAccesoDTO) -> None:
    """Guarda al usuario en la sesión (rota la clave para evitar fijación) y descarta la identidad pendiente."""
    request.session.cycle_key()
    for clave in (CLAVE_PENDIENTE, CLAVE_ESTADO):
        request.session.pop(clave, None)
    request.session.update(
        {
            "id_usuario": resultado.id_usuario,
            "tipo_usuario": resultado.tipo_usuario,
            "rol": resultado.rol,
            "operaciones": list(resultado.operaciones),
            "nombre": resultado.nombre,
            "correo": resultado.correo,
        }
    )


def guardar_identidad_pendiente(request, resultado: ResultadoAccesoDTO) -> None:
    """Visitante sin registrar: la identidad verificada queda en la sesión, nunca en el JSON (P-07)."""
    request.session.cycle_key()
    request.session.pop(CLAVE_ESTADO, None)
    request.session[CLAVE_PENDIENTE] = {
        "identificador_externo": resultado.identificador_externo,
        "nombre": resultado.nombre,
        "correo": resultado.correo,
    }


def identidad_pendiente(request) -> dict[str, str]:
    return request.session[CLAVE_PENDIENTE]


def cerrar_sesion(request) -> None:
    request.session.flush()


def resultado_de_sesion(sesion: SesionUsuario) -> ResultadoAccesoDTO:
    return ResultadoAccesoDTO(
        registrado=True,
        id_usuario=sesion.id_usuario,
        nombre=sesion.nombre,
        correo=sesion.correo,
        tipo_usuario=sesion.tipo_usuario,
        rol=sesion.rol,
        operaciones=sesion.operaciones,
    )


def resultado_de_registro(id_cliente: int, nombre: str, correo: str) -> ResultadoAccesoDTO:
    """Respuesta de ``POST /auth/registro``: el cliente recién creado ya está registrado y no tiene rol."""
    return ResultadoAccesoDTO(
        registrado=True, id_usuario=id_cliente, nombre=nombre, correo=correo, tipo_usuario="CLIENTE"
    )


def a_diccionario(resultado: ResultadoAccesoDTO) -> dict[str, Any]:
    """JSON del ``ResultadoAccesoDTO``: sin ``identificadorExterno`` (P-07) y sin los opcionales nulos."""
    datos = asdict(resultado)
    datos.pop("identificador_externo")
    return {k: v for k, v in datos.items() if v is not None}


# --- OAuth ---------------------------------------------------------------------------------------
def nuevo_estado(request) -> str:
    """Genera el ``state`` de un solo uso y lo guarda en la sesión."""
    estado = secrets.token_urlsafe(32)
    request.session[CLAVE_ESTADO] = estado
    return estado


def consumir_estado(request, recibido: str) -> None:
    """Compara el ``state`` con el de la sesión y lo descarta; si no coincide, 401 AUTORIZACION_FALLIDA."""
    esperado = request.session.pop(CLAVE_ESTADO, None)
    if not esperado or not hmac.compare_digest(esperado.encode(), recibido.encode()):
        raise AutorizacionFallidaError("El estado de la solicitud de acceso no coincide")


def url_de_autorizacion(estado: str, correo: str | None) -> str:
    """URL a la que va el navegador. Sin PKCE: el intercambio lo hace un cliente confidencial (P-19b)."""
    if settings.SIMULAR_EXTERNOS:
        return "/auth/callback?" + urlencode({"code": f"dev:{correo}", "state": estado}, safe=":@")
    parametros = {
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": estado,
    }
    return f"{settings.OIDC_AUTHORIZATION_URL}?{urlencode(parametros)}"
