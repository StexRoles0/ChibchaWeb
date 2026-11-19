"""Soporte (DC-MDO-01): tickets, movimientos y niveles de servicio."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from chibchaweb.dominio._comun import ahora, misma_entidad, propiedad_id, texto_obligatorio
from chibchaweb.dominio.errores import EstadoInvalidoError, NoEncontradoError, ReglaNegocioError, ValidacionError

if TYPE_CHECKING:
    from chibchaweb.dominio.cuentas import Empleado, Usuario
    from chibchaweb.dominio.hospedaje import SitioWeb

_OPERACION_ATENDER = "ATENDER_TICKETS"  # RN-23


class CategoriaTicket(enum.Enum):
    """Tipos de novedad que puede reportar un usuario."""

    RENDIMIENTO = "RENDIMIENTO"
    CORREO = "CORREO"
    BASE_DATOS = "BASE_DATOS"
    DOMINIO = "DOMINIO"
    OTRA = "OTRA"


class EstadoTicket(enum.Enum):
    """Estados de un ticket."""

    ABIERTO = "ABIERTO"
    ESCALADO = "ESCALADO"
    RESUELTO = "RESUELTO"


class NivelServicio:
    """Nivel de atención en la secuencia de escalamiento (Soporte → Gestión → Desarrollo)."""

    id = propiedad_id()

    def __init__(self, nombre: str, orden: int, es_ultimo: bool, id: int | None = None):
        self._id = id
        self._nombre = texto_obligatorio(nombre, "nombre", 40)
        if not isinstance(orden, int) or isinstance(orden, bool) or orden < 1:
            raise ValidacionError("orden", "El orden del nivel debe ser un entero ≥ 1")
        self._orden = orden
        self._es_ultimo = bool(es_ultimo)

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def orden(self) -> int:
        return self._orden

    @property
    def es_ultimo(self) -> bool:
        return self._es_ultimo

    def puede_escalar(self) -> bool:
        return not self._es_ultimo

    def precede(self, otro: NivelServicio) -> bool:
        return self._orden < otro.orden

    def __repr__(self) -> str:
        return f"NivelServicio(id={self._id!r}, nombre={self._nombre!r}, orden={self._orden})"


class MovimientoTicket:
    """Registro de un cambio de estado o de nivel de un ticket."""

    id = propiedad_id()

    def __init__(
        self,
        observacion: str,
        estado_resultante: EstadoTicket,
        nivel_resultante: NivelServicio,
        responsable: Empleado,
        id: int | None = None,
        fecha: datetime | None = None,
    ):
        if not isinstance(estado_resultante, EstadoTicket):
            raise ValidacionError("estadoResultante", "Estado de ticket inválido")
        if nivel_resultante is None or responsable is None:
            raise ValidacionError("responsable", "El movimiento necesita nivel y responsable")
        self._id = id
        self._fecha = fecha or ahora()
        self._observacion = observacion or ""
        self._estado_resultante = estado_resultante
        self._nivel_resultante = nivel_resultante
        self._responsable = responsable

    @property
    def fecha(self) -> datetime:
        return self._fecha

    @property
    def observacion(self) -> str:
        return self._observacion

    @property
    def estado_resultante(self) -> EstadoTicket:
        return self._estado_resultante

    @property
    def nivel_resultante(self) -> NivelServicio:
        return self._nivel_resultante

    @property
    def responsable(self) -> Empleado:
        return self._responsable

    def resulta_en_resolucion(self) -> bool:
        return self._estado_resultante is EstadoTicket.RESUELTO

    def __repr__(self) -> str:
        return f"MovimientoTicket(id={self._id!r}, estado={self._estado_resultante.value})"


class Ticket:
    """Novedad técnica reportada por un usuario, con su nivel actual y su trazabilidad."""

    id = propiedad_id()

    def __init__(
        self,
        descripcion: str,
        categoria: CategoriaTicket,
        reportante: Usuario,
        nivel_actual: NivelServicio,
        id: int | None = None,
        fecha_creacion: datetime | None = None,
        estado: EstadoTicket = EstadoTicket.ABIERTO,
        sitio_afectado: SitioWeb | None = None,
        movimientos: list[MovimientoTicket] | None = None,
    ):
        if not isinstance(categoria, CategoriaTicket):
            raise ValidacionError("categoria", "Categoría de ticket inválida")
        if not isinstance(estado, EstadoTicket):
            raise ValidacionError("estado", "Estado de ticket inválido")
        if reportante is None or nivel_actual is None:
            raise ValidacionError("reportante", "El ticket necesita reportante y nivel")
        self._id = id
        self._descripcion = texto_obligatorio(descripcion, "descripcion", 4000)
        self._fecha_creacion = fecha_creacion or ahora()
        self._categoria = categoria
        self._estado = estado
        self._reportante = reportante
        self._sitio_afectado = sitio_afectado
        self._nivel_actual = nivel_actual
        self._movimientos: list[MovimientoTicket] = list(movimientos or [])
        if id is None:
            self._validar_nuevo()

    def _validar_nuevo(self) -> None:
        """RN-22: un ticket nuevo empieza ABIERTO, en el nivel 1, y el sitio es del cliente que reporta."""
        if not self._reportante.es_autenticable() or not self._reportante.activo:
            raise ReglaNegocioError("Solo un usuario autenticado y activo puede registrar tickets")
        if self._estado is not EstadoTicket.ABIERTO or self._nivel_actual.orden != 1:
            raise ReglaNegocioError("Un ticket nuevo empieza ABIERTO en el nivel de servicio inicial")
        sitio = self._sitio_afectado
        suscripciones = getattr(self._reportante, "suscripciones", None)
        if sitio is not None and suscripciones is not None:
            if not any(s.sitio is sitio or misma_entidad(s.sitio, sitio) for s in suscripciones):
                raise ReglaNegocioError("El sitio afectado no pertenece al cliente")

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @property
    def fecha_creacion(self) -> datetime:
        return self._fecha_creacion

    @property
    def categoria(self) -> CategoriaTicket:
        return self._categoria

    @property
    def estado(self) -> EstadoTicket:
        return self._estado

    @property
    def reportante(self) -> Usuario:
        return self._reportante

    @property
    def sitio_afectado(self) -> SitioWeb | None:
        return self._sitio_afectado

    @property
    def nivel_actual(self) -> NivelServicio:
        return self._nivel_actual

    @property
    def movimientos(self) -> tuple[MovimientoTicket, ...]:
        return tuple(self._movimientos)

    def escalar(self, siguiente: NivelServicio, responsable: Empleado, observacion: str) -> None:
        """RN-23: pasa al nivel siguiente y queda ESCALADO; falla si está resuelto o es el último nivel."""
        observacion = self._preparar_enrutamiento(responsable, observacion)
        if not self._nivel_actual.puede_escalar():
            raise EstadoInvalidoError("El ticket ya está en el último nivel de servicio")
        if siguiente is None or siguiente.orden != self._nivel_actual.orden + 1:
            raise ReglaNegocioError("El nivel destino debe ser el inmediatamente siguiente al actual")
        self._nivel_actual = siguiente
        self._estado = EstadoTicket.ESCALADO
        self._movimientos.append(MovimientoTicket(observacion, self._estado, siguiente, responsable))

    def resolver(self, responsable: Empleado, observacion: str) -> None:
        """RN-23: el ticket queda RESUELTO y se registra el movimiento."""
        observacion = self._preparar_enrutamiento(responsable, observacion)
        self._estado = EstadoTicket.RESUELTO
        self._movimientos.append(MovimientoTicket(observacion, self._estado, self._nivel_actual, responsable))

    def esta_abierto(self) -> bool:
        return self._estado is not EstadoTicket.RESUELTO

    def ultimo_movimiento(self) -> MovimientoTicket:
        if not self._movimientos:
            raise NoEncontradoError("El ticket no tiene movimientos")
        return max(reversed(self._movimientos), key=lambda m: m.fecha)  # empate: el último agregado

    def _preparar_enrutamiento(self, responsable: Empleado, observacion: str) -> str:
        if not self.esta_abierto():
            raise EstadoInvalidoError("El ticket está resuelto y no admite más cambios")
        if responsable is None or not responsable.puede_realizar(_OPERACION_ATENDER):
            raise ReglaNegocioError("Solo un empleado de soporte puede enrutar tickets")
        return texto_obligatorio(observacion, "observacion", 4000)

    def __repr__(self) -> str:
        return f"Ticket(id={self._id!r}, estado={self._estado.value}, nivel={self._nivel_actual.nombre!r})"
