"""MapeadorTicket: ticket con movimientos y sus consultas."""

from datetime import date, datetime

import pytest

from chibchaweb.dominio._comun import ZONA
from chibchaweb.dominio.errores import NoEncontradoError
from chibchaweb.dominio.soporte import CategoriaTicket, EstadoTicket, Ticket


@pytest.fixture
def nivel_inicial(catalogo):
    return catalogo.buscar_nivel_inicial()


@pytest.fixture
def ticket(tickets, cliente, nivel_inicial):
    t = Ticket("El sitio está lento", CategoriaTicket.RENDIMIENTO, cliente, nivel_inicial)
    tickets.insertar(t)
    return t


def test_ida_y_vuelta_con_sitio_y_movimientos(
    tickets, usuarios, suscripciones, cliente, nueva_suscripcion, catalogo, nivel_inicial, empleado_soporte
):
    s = nueva_suscripcion(cliente)
    suscripciones.insertar(s)
    t = Ticket("No carga el correo", CategoriaTicket.CORREO, cliente, nivel_inicial, sitio_afectado=s.sitio)
    t.escalar(catalogo.buscar_nivel_siguiente(nivel_inicial), empleado_soporte, "Pasa a gestión")
    id = tickets.insertar(t)
    assert t.id == id and t.movimientos[0].id
    leido = tickets.buscar_por_id(id)
    assert leido is not t and leido.reportante.id == cliente.id and leido.sitio_afectado.id == s.sitio.id
    assert leido.sitio_afectado is leido.reportante.suscripciones[0].sitio
    assert (leido.descripcion, leido.categoria, leido.estado) == (
        "No carga el correo",
        CategoriaTicket.CORREO,
        EstadoTicket.ESCALADO,
    )
    assert leido.nivel_actual.nombre == "Gestión" and leido.fecha_creacion == t.fecha_creacion
    (m,) = leido.movimientos
    assert (m.observacion, m.estado_resultante, m.nivel_resultante.nombre) == (
        "Pasa a gestión",
        EstadoTicket.ESCALADO,
        "Gestión",
    )
    assert (
        m.responsable.id == empleado_soporte.id
        and m.responsable.puede_realizar("ATENDER_TICKETS")
        and m.fecha == t.movimientos[0].fecha
    )


def test_actualizar_agrega_movimientos_sin_duplicar(tickets, ticket, catalogo, empleado_soporte, nivel_inicial):
    ticket.escalar(catalogo.buscar_nivel_siguiente(nivel_inicial), empleado_soporte, "uno")
    tickets.actualizar(ticket)
    tickets.actualizar(ticket)
    ticket.resolver(empleado_soporte, "listo")
    tickets.actualizar(ticket)
    leido = tickets.buscar_por_id(ticket.id)
    assert leido.estado is EstadoTicket.RESUELTO and [m.observacion for m in leido.movimientos] == ["uno", "listo"]
    assert leido.ultimo_movimiento().resulta_en_resolucion()


def test_consultas(tickets, ticket, usuarios, nuevo_cliente, nivel_inicial, empleado_soporte):
    otro = nuevo_cliente(correo="otro@correo.co", nombre="Pedro Pérez")
    usuarios.insertar(otro)
    cerrado = Ticket("Dominio mal", CategoriaTicket.DOMINIO, otro, nivel_inicial)
    tickets.insertar(cerrado)
    cerrado.resolver(empleado_soporte, "ok")
    tickets.actualizar(cerrado)
    assert [t.id for t in tickets.buscar_abiertos()] == [ticket.id]
    assert [t.id for t in tickets.buscar_por_reportante(otro.id)] == [cerrado.id]
    assert tickets.buscar_por_reportante(999999) == []
    hoy = ticket.fecha_creacion.date()
    assert {t.id for t in tickets.buscar_creados_el(hoy)} == {ticket.id, cerrado.id}
    assert tickets.buscar_creados_el(date(2020, 1, 1)) == []
    assert [t.id for t in tickets.buscar_por_filtro("lento")] == [ticket.id]
    assert [t.id for t in tickets.buscar_por_filtro("pedro")] == [cerrado.id]
    assert len(tickets.buscar_por_filtro("")) == 2
    with pytest.raises(NoEncontradoError):
        tickets.buscar_por_id(999999)


def test_buscar_creados_el_respeta_el_dia_de_bogota(tickets, cliente, nivel_inicial):
    tarde = datetime(2026, 11, 16, 23, 30, tzinfo=ZONA)  # 04:30 UTC del día siguiente
    t = Ticket("Tarde", CategoriaTicket.OTRA, cliente, nivel_inicial, fecha_creacion=tarde)
    tickets.insertar(t)
    assert [x.id for x in tickets.buscar_creados_el(date(2026, 11, 16))] == [t.id]
    assert tickets.buscar_creados_el(date(2026, 11, 17)) == []
