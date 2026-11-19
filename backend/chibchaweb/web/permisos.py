"""Permisos de la API (api.md): ``EsCliente``, ``TieneOperacion("…")`` y variantes."""

from __future__ import annotations

from rest_framework.permissions import BasePermission

from chibchaweb.web.utilidades import CLAVE_PENDIENTE

_OPERACION_POR_TIPO = {
    "CLIENTE": "CONSULTAR_REGISTROS",
    "EMPLEADO": "CONSULTAR_REGISTROS",
    "DISTRIBUIDOR": "CONSULTAR_REGISTROS",
    "TICKET": "ATENDER_TICKETS",
}


class Autenticado(BasePermission):
    """Cualquier usuario con sesión."""

    def has_permission(self, request, view):
        return request.user is not None


class EsCliente(BasePermission):
    """Solo clientes (el cliente no tiene rol)."""

    def has_permission(self, request, view):
        return request.user is not None and request.user.tipo_usuario == "CLIENTE"


class TieneOperacion(BasePermission):
    """La sesión trae la operación pedida (``operaciones`` del rol). Se usa como ``TieneOperacion("X")``."""

    def __init__(self, operacion: str):
        self.operacion = operacion

    def __call__(self):  # DRF instancia cada elemento de ``permission_classes`` llamándolo
        return self

    def has_permission(self, request, view):
        return request.user is not None and request.user.permite(self.operacion)


class TieneOperacionDeConsulta(BasePermission):
    """CON-01/02: CLIENTE, EMPLEADO y DISTRIBUIDOR piden CONSULTAR_REGISTROS; TICKET pide ATENDER_TICKETS."""

    def has_permission(self, request, view):
        if request.user is None:
            return False
        operacion = _OPERACION_POR_TIPO.get(view.kwargs.get("tipo"))
        # Un tipo desconocido pasa: el serializador lo rechaza con 400 SOLICITUD_INVALIDA.
        return operacion is None or request.user.permite(operacion)


class HayIdentidadPendiente(BasePermission):
    """POST /auth/registro: solo con la identidad pendiente de un inicio de sesión (FA2 de AUTH-02)."""

    def has_permission(self, request, view):
        return CLAVE_PENDIENTE in request.session
