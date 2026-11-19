"""Objetos de transferencia y enumeraciones de la capa de servicio (DC-SRV-01).

Son ``@dataclass(frozen=True)`` con los campos del modelo en ``snake_case``. La capa web los convierte a
``camelCase`` con el renderer. Las colecciones ``[0..*]`` son tuplas (solo lectura).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date

from chibchaweb.dominio.soporte import CategoriaTicket  # reexportada: la web no importa el dominio

__all__ = [
    "CategoriaPerfil",
    "CategoriaTicket",
    "DatosClienteDTO",
    "DetalleDTO",
    "DistribuidorDTO",
    "EmpleadoDTO",
    "ResultadoAccesoDTO",
    "ResultadoMigracionDTO",
    "ResumenDTO",
    "TipoEntidad",
]


class CategoriaPerfil(enum.Enum):
    """Bloque de datos que se modifica en una operación de modificación de perfil."""

    PERSONAL = "PERSONAL"
    PAQUETE_PLAN = "PAQUETE_PLAN"
    PAGO = "PAGO"


class TipoEntidad(enum.Enum):
    """Tipo de entidad que reciben las consultas parametrizadas."""

    CLIENTE = "CLIENTE"
    EMPLEADO = "EMPLEADO"
    DISTRIBUIDOR = "DISTRIBUIDOR"
    TICKET = "TICKET"


@dataclass(frozen=True)
class ResultadoAccesoDTO:
    """Resultado de un inicio de sesión: identifica al usuario o trae los datos para prellenar el registro.

    ``identificador_externo`` solo viene con ``registrado = False`` (P-07): la vista lo guarda en la sesión y no
    lo serializa.
    """

    registrado: bool
    nombre: str
    correo: str
    tipo_usuario: str
    id_usuario: int | None = None
    rol: str | None = None
    operaciones: tuple[str, ...] = ()
    identificador_externo: str | None = None


@dataclass(frozen=True)
class DatosClienteDTO:
    """Datos del formulario de registro y de modificación de perfil del cliente.

    En el registro llegan todos los campos de las tres secciones; en la modificación (PATCH) solo los del
    bloque de la ``CategoriaPerfil``, por eso todos admiten ``None`` (el modelo los lista como obligatorios;
    ver pendientes-modelo.md, P-20). ``identificador_externo``, ``nombre`` y ``correo`` son de P-07.
    """

    telefono: str | None = None
    linea_residencia: str | None = None
    ciudad_residencia: str | None = None
    codigo_postal_residencia: str | None = None
    sitio: str | None = None
    plataforma: str | None = None
    id_paquete: int | None = None
    id_plan: int | None = None
    linea_facturacion: str | None = None
    ciudad_facturacion: str | None = None
    codigo_postal_facturacion: str | None = None
    numero_tarjeta: str | None = None
    vencimiento: date | None = None
    codigo_seguridad: str | None = None
    franquicia: str | None = None
    codigo_distribuidor: str | None = None
    id_suscripcion: int | None = None
    identificador_externo: str | None = None
    nombre: str | None = None
    correo: str | None = None

    def __repr__(self) -> str:
        """Sin número de tarjeta ni código de seguridad (RN-12): nunca deben llegar a un log."""
        return f"DatosClienteDTO(correo={self.correo!r}, sitio={self.sitio!r})"


@dataclass(frozen=True)
class EmpleadoDTO:
    """Datos del formulario de alta y edición de empleados."""

    nombre: str
    documento: str
    correo: str
    telefono: str
    id_rol: int


@dataclass(frozen=True)
class DistribuidorDTO:
    """Datos del formulario de alta y edición de distribuidores."""

    nombre: str
    documento: str
    correo: str
    telefono: str


@dataclass(frozen=True)
class ResumenDTO:
    """Vista resumida de un registro en un listado."""

    id: int
    titulo: str
    subtitulo: str
    estado: str


@dataclass(frozen=True)
class DetalleDTO:
    """Vista ampliada de un registro; cada campo es ``"clave: valor"``."""

    id: int
    titulo: str
    campos: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResultadoMigracionDTO:
    """Resultado de la simulación de la migración; cada entrada es ``"NIVEL|tipo|idLegado|mensaje"``."""

    id_proceso: int
    validos: int
    invalidos: int
    entradas: tuple[str, ...] = ()
