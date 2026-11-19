"""Jerarquía de excepciones del dominio (P-09). La capa web las traduce a HTTP (api.md §Errores)."""


class ErrorDominio(Exception):
    """Raíz de todas las excepciones del dominio."""

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class ValidacionError(ErrorDominio):
    """Un dato no cumple su formato o rango. Lleva el campo que falló (422 VALIDACION)."""

    def __init__(self, campo: str, mensaje: str):
        super().__init__(mensaje)
        self.campo = campo


class ReglaNegocioError(ErrorDominio):
    """Se incumple una regla de negocio (422 REGLA_NEGOCIO)."""


class EstadoInvalidoError(ErrorDominio):
    """La transición de estado pedida no está permitida (409 ESTADO_INVALIDO)."""


class NoEncontradoError(ErrorDominio):
    """El objeto pedido no existe (404 NO_ENCONTRADO)."""


class DuplicadoError(ErrorDominio):
    """Un valor que debe ser único ya existe (409 DUPLICADO). Lleva el campo duplicado."""

    def __init__(self, campo: str, mensaje: str):
        super().__init__(mensaje)
        self.campo = campo


class ContingenciaActivaError(ErrorDominio):
    """La BD no está disponible y el evento quedó respaldado en el medio de contingencia (503)."""


class UsuarioInactivoError(ErrorDominio):
    """El usuario fue dado de baja lógica y no puede iniciar sesión (403 USUARIO_INACTIVO, RN-09; P-21)."""


class AutorizacionFallidaError(ErrorDominio):
    """El proveedor OAuth rechazó el código o el ``state`` no coincide (401 AUTORIZACION_FALLIDA; P-21)."""
