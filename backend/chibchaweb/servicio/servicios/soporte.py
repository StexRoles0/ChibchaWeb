"""Soporte (SOP): registro, bandeja diaria y enrutamiento de tickets (CU-SOP-01..03)."""

from __future__ import annotations

from datetime import date

from chibchaweb.dominio.cuentas import Cliente, Empleado
from chibchaweb.dominio.errores import NoEncontradoError, ReglaNegocioError, ValidacionError
from chibchaweb.dominio.repositorios import (
    RepositorioCatalogo,
    RepositorioSuscripcion,
    RepositorioTicket,
    RepositorioUsuario,
)
from chibchaweb.dominio.soporte import CategoriaTicket, Ticket
from chibchaweb.servicio._tiempo import ZONA
from chibchaweb.servicio.dto import ResumenDTO
from chibchaweb.servicio.servicios._comun import _exigir_activo, _resumen_ticket
from chibchaweb.servicio.servicios.consultas import ServicioConsultas


def _recientes_primero(tickets: list[Ticket]) -> list[Ticket]:
    return sorted(tickets, key=lambda t: (t.fecha_creacion, t.id or 0), reverse=True)


class ServicioSoporte:
    """Registro, consulta y enrutamiento de tickets (módulo SOP)."""

    def __init__(
        self,
        consultas: ServicioConsultas,
        usuarios: RepositorioUsuario,
        tickets: RepositorioTicket,
        catalogo: RepositorioCatalogo,
        suscripciones: RepositorioSuscripcion,
    ):
        self._consultas = consultas
        self._usuarios = usuarios
        self._tickets = tickets
        self._catalogo = catalogo
        self._suscripciones = suscripciones

    def registrar_ticket(
        self, id_usuario: int, categoria: CategoriaTicket, descripcion: str, id_sitio: int | None = None
    ) -> int:
        """CU-SOP-01 (RN-22). Cualquier usuario autenticado; empieza ABIERTO en el nivel inicial."""
        usuario = self._usuarios.buscar_por_id(id_usuario)
        _exigir_activo(usuario)
        if not isinstance(categoria, CategoriaTicket):
            raise ValidacionError("categoria", "Categoría de ticket inválida")
        sitio = None
        if id_sitio is not None:
            if not isinstance(usuario, Cliente):
                raise ValidacionError("idSitio", "Solo un cliente puede indicar el sitio afectado")
            try:
                sitio = self._suscripciones.buscar_sitio(id_sitio)
            except NoEncontradoError:
                raise ValidacionError("idSitio", "El sitio no existe") from None
        # El dominio valida RN-22: usuario autenticable y activo, ABIERTO, nivel 1 y sitio del cliente.
        ticket = Ticket(descripcion, categoria, usuario, self._catalogo.buscar_nivel_inicial(), sitio_afectado=sitio)
        return self._tickets.insertar(ticket)

    def consultar_tickets_diario(self, fecha: date) -> list[ResumenDTO]:
        """CU-SOP-02 (RN-24). Unión de los creados ese día y los que siguen abiertos, sin repetir, recientes primero."""
        por_id: dict[int | None, Ticket] = {}
        for ticket in [*self._tickets.buscar_creados_el(fecha), *self._tickets.buscar_abiertos()]:
            if ticket.id in por_id:
                continue
            if ticket.fecha_creacion.astimezone(ZONA).date() == fecha or ticket.esta_abierto():
                por_id[ticket.id] = ticket
        return [_resumen_ticket(t) for t in _recientes_primero(list(por_id.values()))]

    def enrutar_por_nivel_servicio(self, id_ticket: int, id_empleado: int, escalar: bool, observacion: str) -> None:
        """CU-SOP-03 (RN-23). Escala al nivel siguiente o resuelve; el dominio valida estado, rol y observación."""
        ticket = self._tickets.buscar_por_id(id_ticket)
        empleado = self._usuarios.buscar_por_id(id_empleado)
        if not isinstance(empleado, Empleado):
            raise ReglaNegocioError("Solo un empleado de soporte puede enrutar tickets")
        _exigir_activo(empleado)
        if escalar:
            siguiente = self._catalogo.buscar_nivel_siguiente(ticket.nivel_actual)
            ticket.escalar(siguiente, empleado, observacion)  # type: ignore[arg-type]
        else:
            ticket.resolver(empleado, observacion)
        self._tickets.actualizar(ticket)

    def consultar_mis_tickets(self, id_usuario: int) -> list[ResumenDTO]:
        """Tickets que reportó el usuario, del más reciente al más antiguo."""
        return [_resumen_ticket(t) for t in _recientes_primero(self._tickets.buscar_por_reportante(id_usuario))]
