"""CU-SOP-01, CU-SOP-02 y CU-SOP-03: ServicioSoporte con repositorios en memoria."""

from datetime import date, datetime

import pytest

from chibchaweb.dominio.errores import (
    EstadoInvalidoError,
    NoEncontradoError,
    ReglaNegocioError,
    UsuarioInactivoError,
    ValidacionError,
)
from chibchaweb.dominio.soporte import CategoriaTicket, EstadoTicket, Ticket
from chibchaweb.servicio._tiempo import ZONA
from chibchaweb.servicio.dto import ResumenDTO, TipoEntidad


def en(dia: int, hora: int = 10, mes: int = 11) -> datetime:
    return datetime(2026, mes, dia, hora, 0, tzinfo=ZONA)


@pytest.fixture
def ticket(soporte, tickets, cliente_registrado):
    id = soporte.registrar_ticket(cliente_registrado.id, CategoriaTicket.RENDIMIENTO, "El sitio no carga", None)
    return tickets.buscar_por_id(id)


# --- SOP-01 (RN-22) ------------------------------------------------------------------------------
def test_rn22_cliente_registra_ticket_abierto_en_el_nivel_inicial(soporte, tickets, cliente_registrado):
    sitio = cliente_registrado.suscripciones[0].sitio
    id = soporte.registrar_ticket(cliente_registrado.id, CategoriaTicket.CORREO, "No llegan correos", sitio.id)
    t = tickets.buscar_por_id(id)
    assert (t.estado, t.nivel_actual.nombre, t.categoria, t.reportante) == (
        EstadoTicket.ABIERTO,
        "Soporte",
        CategoriaTicket.CORREO,
        cliente_registrado,
    )
    assert t.sitio_afectado is sitio and t.movimientos == ()


def test_rn22_sitio_es_opcional(soporte, tickets, cliente_registrado):
    t = tickets.buscar_por_id(soporte.registrar_ticket(cliente_registrado.id, CategoriaTicket.OTRA, "Duda", None))
    assert t.sitio_afectado is None


def test_rn22_cualquier_empleado_puede_registrar_ticket(soporte, tickets, empleado_gestion, empleado_soporte):
    for e in (empleado_gestion, empleado_soporte):
        t = tickets.buscar_por_id(soporte.registrar_ticket(e.id, CategoriaTicket.OTRA, "Mi equipo falla"))
        assert t.reportante is e and t.nivel_actual.orden == 1


def test_rn22_un_empleado_no_puede_indicar_sitio(soporte, empleado_gestion, cliente_registrado):
    with pytest.raises(ValidacionError) as error:
        soporte.registrar_ticket(
            empleado_gestion.id, CategoriaTicket.OTRA, "x", cliente_registrado.suscripciones[0].sitio.id
        )
    assert error.value.campo == "idSitio"


def test_rn22_el_sitio_debe_ser_del_cliente(soporte, cliente_registrado, cliente_suelto):
    ajeno = cliente_suelto.suscripciones[0].sitio.id
    with pytest.raises(ReglaNegocioError):
        soporte.registrar_ticket(cliente_registrado.id, CategoriaTicket.OTRA, "no es mío", ajeno)


def test_registrar_ticket_con_sitio_inexistente(soporte, cliente_registrado):
    with pytest.raises(ValidacionError) as error:
        soporte.registrar_ticket(cliente_registrado.id, CategoriaTicket.OTRA, "x", 9999)
    assert error.value.campo == "idSitio"


def test_registrar_ticket_valida_descripcion_y_categoria(soporte, tickets, cliente_registrado):
    with pytest.raises(ValidacionError) as descripcion:
        soporte.registrar_ticket(cliente_registrado.id, CategoriaTicket.OTRA, "  ")
    with pytest.raises(ValidacionError) as categoria:
        soporte.registrar_ticket(cliente_registrado.id, "OTRA", "x")  # type: ignore[arg-type]
    assert (descripcion.value.campo, categoria.value.campo) == ("descripcion", "categoria")
    assert tickets.buscar_por_filtro("") == []


def test_registrar_ticket_usuario_inactivo_o_inexistente(soporte, cliente_registrado):
    cliente_registrado.inactivar()
    with pytest.raises(UsuarioInactivoError):
        soporte.registrar_ticket(cliente_registrado.id, CategoriaTicket.OTRA, "x")
    with pytest.raises(NoEncontradoError):
        soporte.registrar_ticket(999, CategoriaTicket.OTRA, "x")


def test_registrar_ticket_un_distribuidor_no_es_autenticable(soporte, distribuidor):
    with pytest.raises(ReglaNegocioError):
        soporte.registrar_ticket(distribuidor.id, CategoriaTicket.OTRA, "x")


def test_mis_tickets_solo_los_del_usuario_recientes_primero(
    soporte, tickets, catalogo, cliente_registrado, cliente_suelto
):
    nivel = catalogo.buscar_nivel_inicial()
    viejo = tickets.insertar(Ticket("viejo", CategoriaTicket.OTRA, cliente_registrado, nivel, fecha_creacion=en(1)))
    nuevo = tickets.insertar(Ticket("nuevo", CategoriaTicket.CORREO, cliente_registrado, nivel, fecha_creacion=en(5)))
    tickets.insertar(Ticket("de otro", CategoriaTicket.OTRA, cliente_suelto, nivel))
    assert soporte.consultar_mis_tickets(cliente_registrado.id) == [
        ResumenDTO(nuevo, "CORREO", "Soporte", "ABIERTO"),
        ResumenDTO(viejo, "OTRA", "Soporte", "ABIERTO"),
    ]
    assert soporte.consultar_mis_tickets(999) == []


# --- SOP-02 (RN-24) ------------------------------------------------------------------------------
def test_rn24_bandeja_une_creados_ese_dia_y_abiertos_sin_repetir(
    soporte, tickets, catalogo, cliente_registrado, empleado_soporte
):
    nivel = catalogo.buscar_nivel_inicial()

    def nuevo(descripcion, dia, hora=10):
        return tickets.insertar(
            Ticket(descripcion, CategoriaTicket.OTRA, cliente_registrado, nivel, fecha_creacion=en(dia, hora))
        )

    resuelto_del_dia = nuevo("resuelto del día", 10, 9)
    abierto_del_dia = nuevo("abierto del día", 10, 15)
    escalado_viejo = nuevo("escalado viejo", 8)
    resuelto_viejo = nuevo("resuelto viejo", 9)
    tickets.buscar_por_id(resuelto_del_dia).resolver(empleado_soporte, "ok")
    tickets.buscar_por_id(resuelto_viejo).resolver(empleado_soporte, "ok")
    tickets.buscar_por_id(escalado_viejo).escalar(
        catalogo.buscar_nivel_siguiente(nivel), empleado_soporte, "pasa a gestión"
    )

    filas = soporte.consultar_tickets_diario(date(2026, 11, 10))

    assert [f.id for f in filas] == [
        abierto_del_dia,
        resuelto_del_dia,
        escalado_viejo,
    ]  # del más reciente al más antiguo
    assert [f.estado for f in filas] == ["ABIERTO", "RESUELTO", "ESCALADO"]
    assert filas[2] == ResumenDTO(escalado_viejo, "OTRA", "Gestión", "ESCALADO")
    assert resuelto_viejo not in [f.id for f in filas]


def test_rn24_un_ticket_abierto_creado_ese_dia_no_se_repite(soporte, tickets, catalogo, cliente_registrado):
    id = tickets.insertar(
        Ticket("x", CategoriaTicket.OTRA, cliente_registrado, catalogo.buscar_nivel_inicial(), fecha_creacion=en(10))
    )
    assert [f.id for f in soporte.consultar_tickets_diario(date(2026, 11, 10))] == [id]


def test_rn24_sin_tickets_la_bandeja_esta_vacia(soporte):
    assert soporte.consultar_tickets_diario(date(2026, 11, 10)) == []


def test_rn24_solo_abiertos_cuando_la_fecha_no_tiene_tickets(soporte, ticket):
    assert [f.id for f in soporte.consultar_tickets_diario(date(2001, 1, 1))] == [ticket.id]


# --- SOP-03 (RN-23) ------------------------------------------------------------------------------
def test_rn23_escalar_pasa_al_nivel_siguiente_con_movimiento(soporte, tickets, ticket, empleado_soporte):
    soporte.enrutar_por_nivel_servicio(ticket.id, empleado_soporte.id, True, "Requiere a gestión")
    t = tickets.buscar_por_id(ticket.id)
    assert (t.estado, t.nivel_actual.nombre) == (EstadoTicket.ESCALADO, "Gestión")
    (m,) = t.movimientos
    assert (m.responsable, m.observacion, m.estado_resultante, m.nivel_resultante.nombre) == (
        empleado_soporte,
        "Requiere a gestión",
        EstadoTicket.ESCALADO,
        "Gestión",
    )


def test_rn23_escalar_hasta_el_ultimo_nivel_y_un_escalamiento_mas_es_409(soporte, tickets, ticket, empleado_soporte):
    soporte.enrutar_por_nivel_servicio(ticket.id, empleado_soporte.id, True, "a gestión")
    soporte.enrutar_por_nivel_servicio(ticket.id, empleado_soporte.id, True, "a desarrollo")
    assert tickets.buscar_por_id(ticket.id).nivel_actual.es_ultimo
    with pytest.raises(EstadoInvalidoError):
        soporte.enrutar_por_nivel_servicio(ticket.id, empleado_soporte.id, True, "más arriba no hay")
    assert len(tickets.buscar_por_id(ticket.id).movimientos) == 2


def test_rn23_resolver_deja_el_ticket_resuelto(soporte, tickets, ticket, empleado_soporte):
    soporte.enrutar_por_nivel_servicio(ticket.id, empleado_soporte.id, False, "Se reinició el servidor")
    t = tickets.buscar_por_id(ticket.id)
    assert (t.estado, t.nivel_actual.nombre, t.movimientos[0].resulta_en_resolucion()) == (
        EstadoTicket.RESUELTO,
        "Soporte",
        True,
    )


@pytest.mark.parametrize("escalar", [True, False])
def test_rn23_un_ticket_resuelto_no_admite_mas_cambios_409(soporte, ticket, empleado_soporte, escalar):
    soporte.enrutar_por_nivel_servicio(ticket.id, empleado_soporte.id, False, "listo")
    with pytest.raises(EstadoInvalidoError):
        soporte.enrutar_por_nivel_servicio(ticket.id, empleado_soporte.id, escalar, "otra vez")


@pytest.mark.parametrize("escalar", [True, False])
def test_rn23_la_observacion_es_obligatoria_422(soporte, tickets, ticket, empleado_soporte, escalar):
    with pytest.raises(ValidacionError) as error:
        soporte.enrutar_por_nivel_servicio(ticket.id, empleado_soporte.id, escalar, "   ")
    assert error.value.campo == "observacion"
    t = tickets.buscar_por_id(ticket.id)
    assert t.estado is EstadoTicket.ABIERTO and t.movimientos == ()


def test_rn23_solo_un_empleado_de_soporte_enruta(soporte, ticket, empleado_gestion, cliente_registrado):
    with pytest.raises(ReglaNegocioError):
        soporte.enrutar_por_nivel_servicio(ticket.id, empleado_gestion.id, True, "yo no atiendo")
    with pytest.raises(ReglaNegocioError):
        soporte.enrutar_por_nivel_servicio(ticket.id, cliente_registrado.id, False, "soy el cliente")


def test_rn23_ticket_o_empleado_inexistente_es_404(soporte, ticket, empleado_soporte):
    with pytest.raises(NoEncontradoError):
        soporte.enrutar_por_nivel_servicio(999, empleado_soporte.id, True, "x")
    with pytest.raises(NoEncontradoError):
        soporte.enrutar_por_nivel_servicio(ticket.id, 999, True, "x")


def test_rn23_un_empleado_inactivo_no_enruta(soporte, ticket, empleado_soporte):
    empleado_soporte.inactivar()
    with pytest.raises(UsuarioInactivoError):
        soporte.enrutar_por_nivel_servicio(ticket.id, empleado_soporte.id, True, "x")


def test_el_detalle_del_ticket_usa_las_convenciones_del_frontend(soporte, consultas, ticket, empleado_soporte):
    soporte.enrutar_por_nivel_servicio(ticket.id, empleado_soporte.id, True, "a gestión")
    campos = dict(c.split(": ", 1) for c in consultas.consultar_detalle(TipoEntidad.TICKET, ticket.id).campos)
    assert (campos["nivel"], campos["estado"], campos["reportante"]) == ("Gestión", "ESCALADO", "Laura Gómez (cliente)")
