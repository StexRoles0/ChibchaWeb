"""Dominios web (DC-MDO-01): solicitud de dominio y su Builder del documento XML."""

from __future__ import annotations

import enum
import re
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from chibchaweb.dominio._comun import ZONA, ahora, propiedad_id
from chibchaweb.dominio.errores import EstadoInvalidoError, ValidacionError

if TYPE_CHECKING:
    from chibchaweb.dominio.cuentas import Cliente
    from chibchaweb.dominio.integraciones import RegistradorDominio

_EXTENSIONES_ADMITIDAS = (".com", ".co", ".net", ".org")
_PATRON_NOMBRE_DOMINIO = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")  # RN-16


class EstadoSolicitud(enum.Enum):
    """Estados de una solicitud de dominio."""

    REGISTRADA = "REGISTRADA"
    ENVIADA = "ENVIADA"
    FALLIDA = "FALLIDA"


class SolicitudDominio:
    """Solicitud de registro de un dominio propio. Es el director del Builder."""

    id = propiedad_id()

    def __init__(
        self,
        nombre: str,
        extension: str,
        solicitante: Cliente,
        id: int | None = None,
        fecha_solicitud: datetime | None = None,
        fecha_envio: datetime | None = None,
        estado: EstadoSolicitud = EstadoSolicitud.REGISTRADA,
    ):
        if solicitante is None:
            raise ValidacionError("solicitante", "La solicitud necesita un solicitante")
        self._id = id
        self._nombre = (nombre or "").strip().lower()  # RN-16: se guarda en minúsculas
        ext = (extension or "").strip().lower()
        self._extension = ext if ext.startswith(".") or not ext else f".{ext}"
        self._fecha_solicitud = fecha_solicitud or ahora()
        self._fecha_envio = fecha_envio
        if not isinstance(estado, EstadoSolicitud):
            raise ValidacionError("estado", "Estado de solicitud inválido")
        self._estado = estado
        self._solicitante = solicitante

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def extension(self) -> str:
        return self._extension

    @property
    def fecha_solicitud(self) -> datetime:
        return self._fecha_solicitud

    @property
    def fecha_envio(self) -> datetime | None:
        return self._fecha_envio

    @property
    def estado(self) -> EstadoSolicitud:
        return self._estado

    @property
    def solicitante(self) -> Cliente:
        return self._solicitante

    def nombre_completo(self) -> str:
        return f"{self._nombre}{self._extension}"

    def validar_formato(self) -> bool:
        """RN-16: 1 a 63 caracteres, letras, dígitos y guiones sin guion extremo; extensión admitida.

        Devuelve ``True`` o lanza ``ValidacionError`` con el ``campo`` que falló (``nombre`` o ``extension``), como
        las demás validaciones del dominio (D-21, P-30).
        """
        if _PATRON_NOMBRE_DOMINIO.match(self._nombre) is None:
            raise ValidacionError(
                "nombre",
                "El nombre debe tener de 1 a 63 letras, dígitos o guiones (sin guion al inicio ni al final)",
            )
        if self._extension not in _EXTENSIONES_ADMITIDAS:
            raise ValidacionError("extension", "La extensión debe ser .com, .co, .net o .org")
        return True

    def esta_pendiente(self) -> bool:
        return self._estado is EstadoSolicitud.REGISTRADA

    def _marcar_enviada(self, fecha: datetime) -> None:
        self._estado = EstadoSolicitud.ENVIADA
        self._fecha_envio = fecha

    def _marcar_fallida(self) -> None:
        self._estado = EstadoSolicitud.FALLIDA

    def construir_documento(self, constructor: ConstructorSolicitud) -> str:
        """Director del Builder (RN-18): invoca los pasos en orden y devuelve el resultado."""
        self.validar_formato()
        constructor.iniciar_documento()
        constructor.agregar_solicitante(self._solicitante)
        constructor.agregar_dominio(self._nombre, self._extension)
        constructor.agregar_fecha(self._fecha_solicitud)
        return constructor.obtener_resultado()

    def enviar_a(self, registrador: RegistradorDominio, documento: str) -> None:
        """RN-17: solo una solicitud pendiente se envía; queda ENVIADA o FALLIDA."""
        if not self.esta_pendiente():
            raise EstadoInvalidoError("Solo se puede enviar una solicitud pendiente")
        if not (documento or "").strip():
            raise ValidacionError("documento", "El documento de la solicitud está vacío")
        try:
            registrador.enviar(documento)
        except Exception:  # falla de red u otro error del registrador externo
            self._marcar_fallida()
            return
        self._marcar_enviada(ahora())

    def __repr__(self) -> str:
        return f"SolicitudDominio(id={self._id!r}, dominio={self.nombre_completo()!r}, estado={self._estado.value})"


class ConstructorSolicitud(ABC):
    """Constructor que arma por partes el documento de la solicitud (Builder)."""

    @abstractmethod
    def iniciar_documento(self) -> None:
        """Inicia un documento vacío."""

    @abstractmethod
    def agregar_solicitante(self, cliente: Cliente) -> None:
        """Agrega los datos del solicitante."""

    @abstractmethod
    def agregar_dominio(self, nombre: str, extension: str) -> None:
        """Agrega el dominio solicitado."""

    @abstractmethod
    def agregar_fecha(self, fecha: date) -> None:
        """Agrega la fecha de la solicitud."""

    @abstractmethod
    def obtener_resultado(self) -> str:
        """Devuelve el documento terminado."""


class ConstructorXML(ConstructorSolicitud):
    """Constructor concreto del XML de ChibchaWEB para los registradores (api.md §Anexo XML)."""

    _ENCABEZADO = '<?xml version="1.0" encoding="UTF-8"?>\n<solicitudDominio>\n'
    _CIERRE = "</solicitudDominio>\n"

    def __init__(self):
        self._contenido = ""

    @property
    def contenido(self) -> str:
        return self._contenido

    def iniciar_documento(self) -> None:
        self._contenido = self._ENCABEZADO

    def agregar_solicitante(self, cliente: Cliente) -> None:
        self._agregar(
            f"  <solicitante><nombre>{escape(cliente.nombre)}</nombre>"
            f"<correo>{escape(cliente.correo)}</correo></solicitante>\n"
        )

    def agregar_dominio(self, nombre: str, extension: str) -> None:
        self._agregar(
            f"  <dominio><nombre>{escape(nombre)}</nombre><extension>{escape(extension)}</extension></dominio>\n"
        )

    def agregar_fecha(self, fecha: date) -> None:
        if isinstance(fecha, datetime):
            texto = (fecha if fecha.tzinfo else fecha.replace(tzinfo=ZONA)).isoformat(timespec="seconds")
        else:
            texto = fecha.isoformat()
        self._agregar(f"  <fecha>{texto}</fecha>\n")

    def obtener_resultado(self) -> str:
        self._exigir_iniciado()
        if not self._contenido.endswith(self._CIERRE):
            self._contenido += self._CIERRE
        return self._contenido

    def _agregar(self, fragmento: str) -> None:
        self._exigir_iniciado()
        if self._contenido.endswith(self._CIERRE):
            raise EstadoInvalidoError("El documento ya fue cerrado")
        self._contenido += fragmento

    def _exigir_iniciado(self) -> None:
        if not self._contenido:
            raise EstadoInvalidoError("Primero se debe iniciar el documento")
