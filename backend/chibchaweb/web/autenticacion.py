"""Autenticación por sesión de Django con CSRF (D-04, D-17). ``django.contrib.auth`` no está instalado."""

from __future__ import annotations

from django.middleware.csrf import get_token
from rest_framework.authentication import BaseAuthentication, CSRFCheck
from rest_framework.exceptions import PermissionDenied

from chibchaweb.servicio.errores import ContingenciaActivaError, UsuarioInactivoError
from chibchaweb.web.utilidades import CLAVE_ESTADO, CLAVE_ID, CLAVE_PENDIENTE, SesionUsuario
from config.contenedor import contenedor


class AutenticacionSesion(BaseAuthentication):
    """Lee al usuario de la sesión y exige el encabezado ``X-CSRFToken`` en los verbos que escriben.

    También exige CSRF cuando la sesión guarda un ``state`` o una identidad pendiente (callback y registro),
    porque en esos casos la cookie de sesión ya autoriza la operación.
    """

    def authenticate(self, request):
        get_token(request)  # deja la cookie csrftoken en toda respuesta para que Angular la lea
        sesion = request.session
        if CLAVE_ID in sesion:
            self._exigir_csrf(request)
            self._refrescar_empleado(request, sesion)
            return SesionUsuario(
                id_usuario=sesion[CLAVE_ID],
                tipo_usuario=sesion["tipo_usuario"],
                rol=sesion.get("rol"),
                operaciones=tuple(sesion.get("operaciones", ())),
                nombre=sesion.get("nombre", ""),
                correo=sesion.get("correo", ""),
            ), None
        if CLAVE_PENDIENTE in sesion or CLAVE_ESTADO in sesion:
            self._exigir_csrf(request)
        return None

    @staticmethod
    def _refrescar_empleado(request, sesion) -> None:
        """La baja lógica de un empleado (EMP-04) cierra sus sesiones y un cambio de cargo (EMP-03) se aplica en la
        siguiente petición: el rol y las operaciones se releen del empleado y no se confía en la cookie (RN-09, P-25).

        Solo se comprueba a los empleados (un cliente se da de baja él mismo y cierra su sesión). Si la BD no
        está disponible (RT04) no se bloquea y rigen los últimos valores de la sesión: la operación pedida
        responderá 503 por su cuenta.
        """
        if sesion.get("tipo_usuario") != "EMPLEADO":
            return
        try:
            actual = contenedor().servicio_acceso.verificar_usuario_activo(sesion[CLAVE_ID])
        except ContingenciaActivaError:
            return
        except UsuarioInactivoError:
            request.session.flush()
            raise
        operaciones = list(actual.operaciones)
        if sesion.get("rol") != actual.rol:
            sesion["rol"] = actual.rol
        if list(sesion.get("operaciones", ())) != operaciones:
            sesion["operaciones"] = operaciones

    def authenticate_header(self, request):
        return "Session"

    @staticmethod
    def _exigir_csrf(request) -> None:
        comprobador = CSRFCheck(lambda peticion: None)
        comprobador.process_request(request)
        motivo = comprobador.process_view(request, None, (), {})
        if motivo:
            raise PermissionDenied(f"CSRF Failed: {motivo}")
