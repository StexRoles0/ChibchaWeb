"""MapeadorSuscripcion: agregado con sitio y pagos, y sus consultas."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from chibchaweb.dominio._comun import ZONA
from chibchaweb.dominio.errores import DuplicadoError, NoEncontradoError
from chibchaweb.dominio.facturacion import EstadoPago, Pago
from chibchaweb.dominio.hospedaje import Plataforma
from tests.falsos import PasarelaPagoFalsa


@pytest.fixture
def suscripcion(usuarios, suscripciones, cliente, nueva_suscripcion):
    s = nueva_suscripcion(cliente)
    suscripciones.insertar(s)
    return s


def test_ida_y_vuelta_con_sitio_y_pagos(usuarios, suscripciones, cliente, nueva_suscripcion):
    s = nueva_suscripcion(cliente)
    s.sitio.asignar_dominio_propio("tiendalaura.co")
    s.agregar_pago(Pago(Decimal("54.00"), EstadoPago.EXITOSO, s, referencia_franquicia="REF-1", comisionado=True))
    s.agregar_pago(Pago(Decimal("54.00"), EstadoPago.FALLIDO, s))
    id = suscripciones.insertar(s)
    assert s.id == id and s.sitio.id and all(p.id for p in s.pagos)
    leida = suscripciones.buscar_por_id(id)
    assert leida is not s and leida.titular.id == cliente.id and leida.titular.medio_pago.numero == "4242424242424242"
    assert (leida.paquete.nombre, leida.plan.nombre) == ("Chibcha-Oro", "Semestral")
    assert (leida.fecha_inicio, leida.fecha_corte, leida.activa) == (s.fecha_inicio, s.fecha_corte, True)
    assert (leida.sitio.subdominio, leida.sitio.dominio_propio, leida.sitio.plataforma) == (
        "tiendalaura.chibchaweb.com",
        "tiendalaura.co",
        Plataforma.UNIX,
    )
    assert leida.monto_del_periodo() == Decimal("54.00")
    assert [(p.monto, p.estado, p.referencia_franquicia, p.comisionado) for p in leida.pagos] == [
        (Decimal("54.00"), EstadoPago.EXITOSO, "REF-1", True),
        (Decimal("54.00"), EstadoPago.FALLIDO, None, False),
    ]
    assert leida.pagos[0].fecha == s.pagos[0].fecha and leida.pagos[0].suscripcion is leida
    assert leida in leida.titular.suscripciones


def test_el_cliente_trae_sus_suscripciones(usuarios, suscripcion, cliente):
    leido = usuarios.buscar_por_id(cliente.id)
    assert [s.id for s in leido.suscripciones] == [suscripcion.id]
    assert leido.suscripciones[0].titular is leido


def test_actualizar_cambia_plan_corte_y_estado(suscripciones, suscripcion, catalogo):
    suscripcion.cambiar_paquete(catalogo.buscar_paquete(3))
    suscripcion.cambiar_plan(catalogo.buscar_plan(4))
    suscripcion.avanzar_corte()
    suscripcion.sitio.subdominio = "otro.chibchaweb.com"
    suscripcion.sitio.plataforma = Plataforma.WINDOWS
    suscripciones.actualizar(suscripcion)
    leida = suscripciones.buscar_por_id(suscripcion.id)
    assert (leida.paquete.nombre, leida.plan.nombre, leida.fecha_corte) == (
        "Chibcha-Platino",
        "Anual",
        suscripcion.fecha_corte,
    )
    assert (leida.sitio.subdominio, leida.sitio.plataforma) == ("otro.chibchaweb.com", Plataforma.WINDOWS)
    suscripcion.suspender()
    suscripciones.actualizar(suscripcion)
    assert suscripciones.buscar_por_id(suscripcion.id).activa is False


def test_registrar_pago_es_idempotente_y_actualizar_no_duplica(suscripciones, suscripcion):
    pago = suscripcion.cobrar(PasarelaPagoFalsa())
    suscripciones.registrar_pago(pago)
    suscripciones.registrar_pago(pago)  # ya tiene id: no se vuelve a insertar
    suscripciones.actualizar(suscripcion)  # actualizar no toca los pagos
    leida = suscripciones.buscar_por_id(suscripcion.id)
    assert len(leida.pagos) == 1 and leida.pagos[0].id == pago.id and leida.fecha_corte == suscripcion.fecha_corte


def test_d30_registrar_un_pago_exitoso_deja_pago_y_corte_juntos_y_uno_fallido_no_mueve_el_corte(
    suscripciones, suscripcion
):
    inicial = suscripcion.fecha_corte
    fallido = Pago(Decimal("54.00"), EstadoPago.FALLIDO, suscripcion)
    suscripcion.agregar_pago(fallido)
    suscripciones.registrar_pago(fallido)
    assert suscripciones.buscar_por_id(suscripcion.id).fecha_corte == inicial

    pago = suscripcion.cobrar(PasarelaPagoFalsa())  # exitoso: avanza el corte en memoria
    suscripciones.registrar_pago(pago)  # sin llamar a actualizar: el corte viaja con el pago
    leida = suscripciones.buscar_por_id(suscripcion.id)
    assert leida.fecha_corte == suscripcion.fecha_corte != inicial and len(leida.pagos) == 2


def test_buscar_vencidas(suscripciones, suscripcion):
    assert suscripciones.buscar_vencidas(date(2026, 11, 15)) == []
    assert [s.id for s in suscripciones.buscar_vencidas(date(2026, 11, 16))] == [suscripcion.id]
    suscripcion.suspender()
    suscripciones.actualizar(suscripcion)
    assert suscripciones.buscar_vencidas(date(2030, 1, 1)) == []


def test_buscar_por_filtro_y_sitio(suscripciones, suscripcion):
    assert [s.id for s in suscripciones.buscar_por_filtro("tiendalaura")] == [suscripcion.id]
    assert [s.id for s in suscripciones.buscar_por_filtro("laura gómez")] == [suscripcion.id]
    assert suscripciones.buscar_por_filtro("zzz") == []
    assert len(suscripciones.buscar_por_filtro("")) == 1
    assert suscripciones.buscar_sitio(suscripcion.sitio.id).subdominio == "tiendalaura.chibchaweb.com"
    with pytest.raises(NoEncontradoError):
        suscripciones.buscar_sitio(999999)
    with pytest.raises(NoEncontradoError):
        suscripciones.buscar_por_id(999999)


def test_subdominio_duplicado(suscripciones, suscripcion, cliente, nueva_suscripcion):
    with pytest.raises(DuplicadoError) as e:
        suscripciones.insertar(nueva_suscripcion(cliente))
    assert e.value.campo == "sitio"


def test_pagos_para_comision_filtra_por_distribuidor_periodo_y_estado(
    usuarios, suscripciones, nuevo_cliente, distribuidor, nueva_suscripcion
):
    referido = nuevo_cliente(correo="ref@correo.co")
    referido.asociar_distribuidor(distribuidor)
    usuarios.insertar(referido)
    libre = nuevo_cliente(correo="libre@correo.co")
    usuarios.insertar(libre)
    s1, s2 = nueva_suscripcion(referido, "uno"), nueva_suscripcion(libre, "dos")
    ahora = datetime(2026, 12, 15, 12, 0, tzinfo=ZONA)
    fuera = datetime(2027, 2, 1, 12, 0, tzinfo=ZONA)
    s1.agregar_pago(Pago(Decimal("10.00"), EstadoPago.EXITOSO, s1, fecha=ahora, referencia_franquicia="A"))
    s1.agregar_pago(Pago(Decimal("11.00"), EstadoPago.EXITOSO, s1, fecha=fuera, referencia_franquicia="B"))
    s1.agregar_pago(Pago(Decimal("12.00"), EstadoPago.FALLIDO, s1, fecha=ahora))
    s1.agregar_pago(
        Pago(Decimal("13.00"), EstadoPago.EXITOSO, s1, fecha=ahora, referencia_franquicia="C", comisionado=True)
    )
    s2.agregar_pago(Pago(Decimal("14.00"), EstadoPago.EXITOSO, s2, fecha=ahora, referencia_franquicia="D"))
    suscripciones.insertar(s1)
    suscripciones.insertar(s2)
    pagos = suscripciones.buscar_pagos_para_comision(distribuidor, date(2026, 12, 1), date(2026, 12, 31))
    assert [p.monto for p in pagos] == [Decimal("10.00")]
    assert pagos[0].suscripcion.titular.distribuidor is distribuidor and pagos[0].esta_disponible_para_comision()
    # el último día del periodo cuenta completo
    assert len(suscripciones.buscar_pagos_para_comision(distribuidor, date(2026, 12, 15), date(2026, 12, 15))) == 1
