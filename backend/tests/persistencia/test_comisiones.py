"""MapeadorComision: comisión con pagos base y cheque."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from django.db import connection

from chibchaweb.dominio._comun import ZONA
from chibchaweb.dominio.errores import DuplicadoError, NoEncontradoError, ValidacionError
from chibchaweb.dominio.facturacion import Cheque, Comision, EstadoPago, Pago

PERIODO = (date(2026, 12, 1), date(2026, 12, 31))


@pytest.fixture
def escenario(usuarios, suscripciones, nuevo_cliente, distribuidor, nueva_suscripcion):
    """Un referido con una suscripción y dos pagos exitosos del periodo."""
    referido = nuevo_cliente(correo="ref@correo.co")
    referido.asociar_distribuidor(distribuidor)
    distribuidor.agregar_referido(referido)
    usuarios.insertar(referido)
    s = nueva_suscripcion(referido, "referido")
    fecha = datetime(2026, 12, 10, 9, 0, tzinfo=ZONA)
    for ref, monto in (("R1", "50.00"), ("R2", "30.00")):
        s.agregar_pago(Pago(Decimal(monto), EstadoPago.EXITOSO, s, fecha=fecha, referencia_franquicia=ref))
    suscripciones.insertar(s)
    return distribuidor, s


@pytest.fixture
def comision(escenario, suscripciones, comisiones):
    distribuidor, _ = escenario
    c = Comision(*PERIODO, 1, "Básico", Decimal("0.10"), distribuidor)
    for pago in suscripciones.buscar_pagos_para_comision(distribuidor, *PERIODO):
        c.agregar_pago_base(pago)
    comisiones.insertar(c)
    return c


def test_ida_y_vuelta_y_marca_de_pagos(comisiones, comision, suscripciones, escenario):
    distribuidor, s = escenario
    assert comision.id and comision.calcular_monto() == Decimal("8.00")
    leida = comisiones.buscar_por_id(comision.id)
    assert (
        leida is not comision and leida.beneficiario.id == distribuidor.id and leida.beneficiario.codigo == "DIS-TEST01"
    )
    assert (leida.fecha_inicio, leida.fecha_fin, leida.clientes_referidos) == (*PERIODO, 1)
    assert (leida.nombre_categoria, leida.porcentaje) == ("Básico", Decimal("0.10"))
    assert sorted(p.monto for p in leida.pagos_base) == [Decimal("30.00"), Decimal("50.00")]
    assert all(p.comisionado for p in leida.pagos_base) and leida.calcular_monto() == Decimal("8.00")
    assert leida.cheque is None and not leida.tiene_cheque()
    assert suscripciones.buscar_pagos_para_comision(distribuidor, *PERIODO) == []  # ya comisionados
    with connection.cursor() as c:
        c.execute("SELECT count(*) FROM pago WHERE id_comision=%s", [comision.id])
        assert c.fetchone()[0] == 2


def test_registrar_cheque_y_recargar(comisiones, comision):
    comision.asociar_cheque(Cheque("CHQ-2026-000001", "Andes Digital 2", Decimal("8.00"), date(2027, 1, 1)))
    comisiones.registrar_cheque(comision)
    comisiones.registrar_cheque(comision)  # idempotente
    assert comision.cheque.id
    leida = comisiones.buscar_por_id(comision.id)
    assert leida.tiene_cheque()
    assert (leida.cheque.numero, leida.cheque.beneficiario, leida.cheque.monto, leida.cheque.fecha_emision) == (
        "CHQ-2026-000001",
        "Andes Digital 2",
        Decimal("8.00"),
        date(2027, 1, 1),
    )
    assert leida.cheque.monto_en_letras() == "OCHO DÓLARES CON 00/100"


def test_cheque_duplicado_y_sin_cheque(comisiones, comision):
    with pytest.raises(ValidacionError):
        comisiones.registrar_cheque(comision)
    comision.asociar_cheque(Cheque("CHQ-2026-000002", "X", Decimal("8.00"), date(2027, 1, 1)))
    comisiones.registrar_cheque(comision)
    repetido = Cheque("CHQ-2026-000002", "X", Decimal("1.00"), date(2027, 1, 1))
    with pytest.raises(DuplicadoError) as e:
        comisiones.insertar(Comision(*PERIODO, 1, "Básico", Decimal("0.10"), comision.beneficiario, cheque=repetido))
    assert e.value.campo == "numero"


def test_insertar_con_cheque_y_actualizar(comisiones, escenario, suscripciones):
    distribuidor, s = escenario
    c = Comision(*PERIODO, 1, "Básico", Decimal("0.10"), distribuidor)
    for pago in suscripciones.buscar_pagos_para_comision(distribuidor, *PERIODO)[:1]:
        c.agregar_pago_base(pago)
    c.asociar_cheque(Cheque("CHQ-2026-000009", "Andes", c.calcular_monto(), date(2027, 1, 2)))
    comisiones.insertar(c)
    assert c.cheque.id and comisiones.buscar_por_id(c.id).cheque.numero == "CHQ-2026-000009"
    segundo = suscripciones.buscar_pagos_para_comision(distribuidor, *PERIODO)
    assert len(segundo) == 1
    c2 = Comision(*PERIODO, 1, "Premium", Decimal("0.15"), distribuidor)
    comisiones.insertar(c2)
    c2.agregar_pago_base(segundo[0])
    comisiones.actualizar(c2)
    assert len(comisiones.buscar_por_id(c2.id).pagos_base) == 1


def test_buscar_por_filtro_y_no_encontrada(comisiones, comision):
    assert [c.id for c in comisiones.buscar_por_filtro("andes")] == [comision.id]
    assert [c.id for c in comisiones.buscar_por_filtro("DIS-TEST")] == [comision.id]
    assert [c.id for c in comisiones.buscar_por_filtro("básico")] == [comision.id]
    assert comisiones.buscar_por_filtro("zzz") == []
    with pytest.raises(NoEncontradoError):
        comisiones.buscar_por_id(999999)


def test_actualizar_con_cheque_sin_id_falla_en_vez_de_descartarlo(comisiones, comision):
    comision.asociar_cheque(Cheque("CHQ-2026-000003", "Andes", Decimal("8.00"), date(2027, 1, 1)))
    with pytest.raises(RuntimeError, match="registrar_cheque"):
        comisiones.actualizar(comision)
    comisiones.registrar_cheque(comision)
    comisiones.actualizar(comision)  # con el cheque ya escrito, actualizar funciona
