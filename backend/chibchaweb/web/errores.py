"""``exception_handler`` de DRF: jerarquía ``ErrorDominio`` y errores de DRF -> cuerpo y código de api.md §Errores."""

from __future__ import annotations

import logging

from django.db import Error as ErrorBD
from django.db import InterfaceError, OperationalError
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response

from chibchaweb.servicio.errores import (
    AutorizacionFallidaError,
    ContingenciaActivaError,
    DuplicadoError,
    ErrorDominio,
    EstadoInvalidoError,
    NoEncontradoError,
    ReglaNegocioError,
    UsuarioInactivoError,
    ValidacionError,
)

logger = logging.getLogger(__name__)


def _cuerpo(codigo: str, mensaje: str, campo: str | None = None) -> dict[str, str]:
    cuerpo = {"codigo": codigo, "mensaje": mensaje}
    if campo:
        cuerpo["campo"] = campo
    return cuerpo


def traducir(exc: Exception) -> tuple[int, dict[str, str]] | None:
    """Devuelve ``(estado HTTP, cuerpo)`` o ``None`` si la excepción no es una que la API conozca."""
    if isinstance(exc, ValidacionError):
        return 422, _cuerpo("VALIDACION", exc.mensaje, exc.campo)
    if isinstance(exc, DuplicadoError):
        codigo = "SUBDOMINIO_EN_USO" if exc.campo == "sitio" else "DUPLICADO"
        return 409, _cuerpo(codigo, exc.mensaje, exc.campo)
    if isinstance(exc, EstadoInvalidoError):
        return 409, _cuerpo("ESTADO_INVALIDO", exc.mensaje)
    if isinstance(exc, ReglaNegocioError):
        return 422, _cuerpo("REGLA_NEGOCIO", exc.mensaje)
    if isinstance(exc, NoEncontradoError):
        return 404, _cuerpo("NO_ENCONTRADO", exc.mensaje)
    if isinstance(exc, ContingenciaActivaError):
        return 503, _cuerpo("CONTINGENCIA", exc.mensaje)
    if isinstance(exc, OperationalError | InterfaceError):
        # La BD cayó donde ningún mapeador pudo respaldar nada (p. ej. al abrir la transacción de la petición,
        # que siempre ocurre antes de la primera lectura): no hay evento que guardar. D-30.
        return 503, _cuerpo("CONTINGENCIA", "La base de datos no está disponible; intente de nuevo más tarde")
    if isinstance(exc, UsuarioInactivoError):
        return 403, _cuerpo("USUARIO_INACTIVO", exc.mensaje)
    if isinstance(exc, AutorizacionFallidaError):  # P-19, P-21
        return 401, _cuerpo("AUTORIZACION_FALLIDA", exc.mensaje)
    if isinstance(exc, ErrorDominio):
        return 422, _cuerpo("REGLA_NEGOCIO", exc.mensaje)
    return None


def _campo_de(detalle) -> tuple[str | None, str]:
    """Primer campo con error del serializador (en camelCase) y su mensaje."""
    if isinstance(detalle, dict):
        for campo, mensajes in detalle.items():
            primero = mensajes[0] if isinstance(mensajes, list | tuple) and mensajes else mensajes
            texto = _campo_de(primero)[1] if isinstance(primero, dict) else str(primero)
            partes = str(campo).split("_")
            return partes[0] + "".join(p.title() for p in partes[1:]), texto
    if isinstance(detalle, list | tuple) and detalle:
        return None, str(detalle[0])
    return None, str(detalle)


def manejador(exc: Exception, contexto) -> Response | None:
    """Manejador registrado en ``REST_FRAMEWORK['EXCEPTION_HANDLER']``."""
    traducido = traducir(exc)
    if traducido is not None:
        estado, cuerpo = traducido
        return Response(cuerpo, status=estado)
    if isinstance(exc, exceptions.NotAuthenticated | exceptions.AuthenticationFailed):
        return Response(_cuerpo("NO_AUTENTICADO", "Debe iniciar sesión"), status=401)
    if isinstance(exc, exceptions.PermissionDenied):
        return Response(_cuerpo("SIN_PERMISO", str(exc.detail)), status=403)
    if isinstance(exc, Http404 | exceptions.NotFound):
        return Response(_cuerpo("NO_ENCONTRADO", "El recurso no existe"), status=404)
    if isinstance(exc, exceptions.ValidationError):
        campo, mensaje = _campo_de(exc.detail)
        return Response(_cuerpo("SOLICITUD_INVALIDA", mensaje, campo), status=400)
    if isinstance(exc, exceptions.APIException):
        return Response(_cuerpo("SOLICITUD_INVALIDA", str(exc.detail)), status=exc.status_code)
    if isinstance(exc, ErrorBD):
        # IntegrityError/DataError/... no previstos: se registran y se responde un 500 JSON genérico (sin detalles).
        logger.error("Error de base de datos no previsto", exc_info=exc)
        return Response(_cuerpo("ERROR_INTERNO", "Ocurrió un error interno; intente de nuevo más tarde"), status=500)
    return None  # error no previsto: Django responde 500
