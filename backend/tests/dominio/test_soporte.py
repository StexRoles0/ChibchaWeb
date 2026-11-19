"""Soporte: RN-22 y RN-23 (RN-24 vive en el servicio; se comprueba el apoyo del dominio)."""

from datetime import datetime

import pytest
from freezegun import freeze_time

from chibchaweb.dominio._comun import ZONA
from chibchaweb.dominio.errores import EstadoInvalidoError, NoEncontradoError, ReglaNegocioError, ValidacionError
from chibchaweb.dominio.soporte import CategoriaTicket, EstadoTicket, MovimientoTicket, NivelServicio, Ticket


@pytest.fixture
def niveles(catalogo):
    return catalogo.niveles


@pytest.fixture
def ticket(cliente, niveles):
    return Ticket("El sitio está caído", CategoriaTicket.RENDIMIENTO, cliente, niveles[0])


# --- Niveles -----------------------------------------------------------------------------------


def test_niveles_ordenados(niveles):
    soporte, gestion, desarrollo = niveles
    assert soporte.puede_escalar() and gestion.puede_escalar() and not desarrollo.puede_escalar()
    assert soporte.precede(gestion) and not desarrollo.precede(soporte)
    assert (desarrollo.nombre, desarrollo.orden, desarrollo.es_ultimo) == ("Desarrollo", 3, True)
    assert "Desarrollo" in repr(desarrollo)
    with pytest.raises(ValidacionError):
        NivelServicio("X", 0, False)


# --- RN-22 registro ----------------------------------------------------------------------------


def test_rn22_ticket_nuevo_abierto_en_nivel_inicial(ticket, cliente, niveles):
    assert ticket.estado is EstadoTicket.ABIERTO and ticket.nivel_actual is niveles[0]
    assert ticket.esta_abierto() and ticket.reportante is cliente and ticket.movimientos == ()
    assert ticket.categoria is CategoriaTicket.RENDIMIENTO and ticket.descripcion == "El sitio está caído"
    assert ticket.sitio_afectado is None and "ABIERTO" in repr(ticket)


def test_rn22_ticket_nuevo_no_puede_empezar_en_otro_nivel_o_estado(cliente, niveles):
    with pytest.raises(ReglaNegocioError):
        Ticket("x", CategoriaTicket.OTRA, cliente, niveles[1])
    with pytest.raises(ReglaNegocioError):
        Ticket("x", CategoriaTicket.OTRA, cliente, niveles[0], estado=EstadoTicket.ESCALADO)


def test_rn22_empleado_tambien_registra(empleado_soporte, niveles):
    t = Ticket("Correo lento", CategoriaTicket.CORREO, empleado_soporte, niveles[0])
    assert t.reportante is empleado_soporte


def test_rn22_distribuidor_o_inactivo_no_registra(distribuidor, cliente, niveles):
    with pytest.raises(ReglaNegocioError):
        Ticket("x", CategoriaTicket.OTRA, distribuidor, niveles[0])
    cliente.inactivar()
    with pytest.raises(ReglaNegocioError):
        Ticket("x", CategoriaTicket.OTRA, cliente, niveles[0])


def test_rn22_sitio_afectado_debe_ser_del_cliente(cliente, nuevo_cliente, nueva_suscripcion, niveles):
    propia = nueva_suscripcion(cliente, sitio="propio", id=1)
    t = Ticket("x", CategoriaTicket.DOMINIO, cliente, niveles[0], sitio_afectado=propia.sitio)
    assert t.sitio_afectado is propia.sitio
    ajena = nueva_suscripcion(nuevo_cliente(correo="o@x.co", id=99), sitio="ajeno", id=2)
    with pytest.raises(ReglaNegocioError):
        Ticket("x", CategoriaTicket.DOMINIO, cliente, niveles[0], sitio_afectado=ajena.sitio)


def test_rn22_validaciones_basicas(cliente, niveles):
    with pytest.raises(ValidacionError):
        Ticket("   ", CategoriaTicket.OTRA, cliente, niveles[0])
    with pytest.raises(ValidacionError):
        Ticket("x", "OTRA", cliente, niveles[0])  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        Ticket("x", CategoriaTicket.OTRA, cliente, niveles[0], estado="ABIERTO")  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        Ticket("x", CategoriaTicket.OTRA, None, niveles[0])  # type: ignore[arg-type]
    assert [c.value for c in CategoriaTicket] == ["RENDIMIENTO", "CORREO", "BASE_DATOS", "DOMINIO", "OTRA"]


def test_ticket_reconstruido_no_revalida_reglas_de_alta(cliente, niveles):
    t = Ticket("x", CategoriaTicket.OTRA, cliente, niveles[2], id=5, estado=EstadoTicket.ESCALADO)
    assert t.id == 5 and t.nivel_actual is niveles[2]


# --- RN-23 enrutamiento ------------------------------------------------------------------------


def test_rn23_escalar_pasa_al_siguiente_nivel_y_registra_movimiento(ticket, niveles, empleado_soporte):
    ticket.escalar(niveles[1], empleado_soporte, "Requiere revisión de gestión")
    assert ticket.estado is EstadoTicket.ESCALADO and ticket.nivel_actual is niveles[1]
    mov = ticket.ultimo_movimiento()
    assert isinstance(mov, MovimientoTicket)
    assert (mov.estado_resultante, mov.nivel_resultante, mov.responsable, mov.observacion) == (
        EstadoTicket.ESCALADO,
        niveles[1],
        empleado_soporte,
        "Requiere revisión de gestión",
    )
    assert not mov.resulta_en_resolucion() and "ESCALADO" in repr(mov)


def test_rn23_escalar_falla_en_el_ultimo_nivel(ticket, niveles, empleado_soporte):
    ticket.escalar(niveles[1], empleado_soporte, "a")
    ticket.escalar(niveles[2], empleado_soporte, "b")
    with pytest.raises(EstadoInvalidoError):
        ticket.escalar(niveles[2], empleado_soporte, "c")


def test_rn23_escalar_solo_al_nivel_inmediatamente_siguiente(ticket, niveles, empleado_soporte):
    with pytest.raises(ReglaNegocioError):
        ticket.escalar(niveles[2], empleado_soporte, "salto")  # no se salta el nivel 2
    assert ticket.nivel_actual is niveles[0] and ticket.movimientos == ()


def test_rn23_escalar_hacia_un_nivel_no_posterior_falla(ticket, niveles, empleado_soporte):
    with pytest.raises(ReglaNegocioError):
        ticket.escalar(niveles[0], empleado_soporte, "a")
    with pytest.raises(ReglaNegocioError):
        ticket.escalar(None, empleado_soporte, "a")  # type: ignore[arg-type]


def test_rn23_resolver_y_ya_no_admite_cambios(ticket, niveles, empleado_soporte):
    ticket.resolver(empleado_soporte, "Se reinició el servidor")
    assert ticket.estado is EstadoTicket.RESUELTO and not ticket.esta_abierto()
    assert ticket.ultimo_movimiento().resulta_en_resolucion()
    assert ticket.ultimo_movimiento().nivel_resultante is niveles[0]
    with pytest.raises(EstadoInvalidoError):
        ticket.escalar(niveles[1], empleado_soporte, "x")
    with pytest.raises(EstadoInvalidoError):
        ticket.resolver(empleado_soporte, "x")


def test_rn23_observacion_obligatoria(ticket, empleado_soporte):
    with pytest.raises(ValidacionError) as e:
        ticket.resolver(empleado_soporte, "  ")
    assert e.value.campo == "observacion"


def test_rn23_solo_soporte_enruta(ticket, nuevo_empleado, niveles):
    gestion = nuevo_empleado(rol_id=1, correo="gestion@chibchaweb.co", id=21)
    with pytest.raises(ReglaNegocioError):
        ticket.resolver(gestion, "x")
    with pytest.raises(ReglaNegocioError):
        ticket.escalar(niveles[1], gestion, "x")


def test_ultimo_movimiento(ticket, niveles, empleado_soporte):
    with pytest.raises(NoEncontradoError):
        ticket.ultimo_movimiento()
    with freeze_time("2026-11-16 15:00:00"):
        ticket.escalar(niveles[1], empleado_soporte, "primero")
        ticket.resolver(empleado_soporte, "segundo")  # misma hora: gana el último agregado
    assert ticket.ultimo_movimiento().observacion == "segundo"
    assert len(ticket.movimientos) == 2
    assert ticket.ultimo_movimiento().fecha == datetime(2026, 11, 16, 10, 0, tzinfo=ZONA)


def test_movimiento_validaciones(niveles, empleado_soporte):
    with pytest.raises(ValidacionError):
        MovimientoTicket("x", "RESUELTO", niveles[0], empleado_soporte)  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        MovimientoTicket("x", EstadoTicket.RESUELTO, niveles[0], None)  # type: ignore[arg-type]


# --- RN-24 (servicio): el dominio aporta esta_abierto y fecha_creacion --------------------------


def test_rn24_apoyo_del_dominio_para_la_bandeja(cliente, niveles, empleado_soporte):
    with freeze_time("2026-11-15 15:00:00"):
        viejo = Ticket("viejo", CategoriaTicket.OTRA, cliente, niveles[0])
    with freeze_time("2026-11-16 15:00:00"):
        nuevo = Ticket("nuevo", CategoriaTicket.OTRA, cliente, niveles[0])
    nuevo.resolver(empleado_soporte, "ok")
    assert viejo.esta_abierto() and not nuevo.esta_abierto()
    assert nuevo.fecha_creacion > viejo.fecha_creacion
