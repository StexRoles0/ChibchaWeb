"""Excepciones que la capa web necesita traducir a HTTP.

La web no puede importar el dominio (docs/arquitectura.md §1), así que el servicio las reexporta: son las mismas
clases de ``chibchaweb.dominio.errores`` (P-09), no clases nuevas.
"""

from chibchaweb.dominio.errores import (
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

__all__ = [
    "AutorizacionFallidaError",
    "ContingenciaActivaError",
    "DuplicadoError",
    "ErrorDominio",
    "EstadoInvalidoError",
    "NoEncontradoError",
    "ReglaNegocioError",
    "UsuarioInactivoError",
    "ValidacionError",
]
