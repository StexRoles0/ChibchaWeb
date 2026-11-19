"""Pagos, comisiones y cheques: RN-19, RN-20 y RN-21."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from chibchaweb.dominio._comun import ZONA
from chibchaweb.dominio.errores import ReglaNegocioError, ValidacionError
from chibchaweb.dominio.facturacion import (
    CategoriaBasica,
    CategoriaDistribuidor,
    CategoriaPremium,
    Cheque,
    Comision,
    EstadoPago,
    Pago,
)


def _pago(suscripcion, monto="54.00", dia=15, estado=EstadoPago.EXITOSO, comisionado=False):
    return Pago(
        Decimal(monto),
        estado,
        suscripcion,
        fecha=datetime(2026, 11, dia, 10, 0, tzinfo=ZONA),
        referencia_franquicia="REF-1" if estado is EstadoPago.EXITOSO else None,
        comisionado=comisionado,
    )


@pytest.fixture
def referido(cliente, distribuidor, nueva_suscripcion):
    cliente.asociar_distribuidor(distribuidor)
    distribuidor.agregar_referido(cliente)
    return nueva_suscripcion(cliente, id=1)


@pytest.fixture
def comision(distribuidor):
    return Comision(date(2026, 11, 1), date(2026, 11, 30), 1, "Básico", Decimal("0.10"), distribuidor, id=7)


# --- Pago ------------------------------------------------------------------------------------


def test_pago_estados_y_disponibilidad(referido):
    exitoso = _pago(referido)
    assert exitoso.es_exitoso() and exitoso.esta_disponible_para_comision()
    exitoso.marcar_comisionado()
    assert exitoso.comisionado and not exitoso.esta_disponible_para_comision()
    with pytest.raises(ReglaNegocioError):
        exitoso.marcar_comisionado()
    fallido = _pago(referido, estado=EstadoPago.FALLIDO)
    assert not fallido.es_exitoso() and not fallido.esta_disponible_para_comision()
    assert [e.value for e in EstadoPago] == ["EXITOSO", "FALLIDO"]
    assert "EXITOSO" in repr(exitoso) and exitoso.fecha.day == 15 and exitoso.monto == Decimal("54.00")


def test_pago_validaciones(referido):
    with pytest.raises(ValidacionError):
        Pago(Decimal("0"), EstadoPago.EXITOSO, referido, referencia_franquicia="R")
    with pytest.raises(ValidacionError):
        Pago(Decimal("1"), EstadoPago.EXITOSO, referido)  # sin referencia
    with pytest.raises(ValidacionError):
        Pago(Decimal("1"), EstadoPago.FALLIDO, referido, referencia_franquicia="R")
    with pytest.raises(ValidacionError):
        Pago(Decimal("1"), "EXITOSO", referido, referencia_franquicia="R")  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        Pago(Decimal("1"), EstadoPago.EXITOSO, None, referencia_franquicia="R")  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        Pago(Decimal("1"), EstadoPago.EXITOSO, referido, referencia_franquicia="R" * 101)


# --- RN-19 categorías (Strategy) ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("cantidad", "basica", "premium"), [(0, True, False), (100, True, False), (101, False, True), (5000, False, True)]
)
def test_rn19_limites_de_categoria(cantidad, basica, premium):
    assert CategoriaBasica().aplica_a(cantidad) is basica
    assert CategoriaPremium().aplica_a(cantidad) is premium


def test_rn19_nombre_y_porcentaje_de_cada_estrategia():
    b, p = CategoriaBasica(), CategoriaPremium()
    assert isinstance(b, CategoriaDistribuidor) and isinstance(p, CategoriaDistribuidor)
    assert (b.nombre(), b.porcentaje(), b.porcentaje_comision, b.limite_superior) == (
        "Básico",
        Decimal("0.10"),
        Decimal("0.10"),
        100,
    )
    assert (p.nombre(), p.porcentaje(), p.porcentaje_comision, p.limite_inferior) == (
        "Premium",
        Decimal("0.15"),
        Decimal("0.15"),
        101,
    )
    with pytest.raises(ValidacionError):
        b.aplica_a(-1)
    with pytest.raises(TypeError):
        CategoriaDistribuidor()  # type: ignore[abstract]


# --- RN-20 comisión ----------------------------------------------------------------------------


def test_rn20_monto_es_suma_de_pagos_por_porcentaje(comision, referido):
    p1, p2 = _pago(referido, "54.00"), _pago(referido, "28.50", dia=20)
    comision.agregar_pago_base(p1)
    comision.agregar_pago_base(p2)
    assert comision.calcular_monto() == Decimal("8.25")  # 82.50 × 0.10
    assert p1.comisionado and p2.comisionado
    assert comision.pagos_base == (p1, p2)


def test_rn20_premium_15_por_ciento(distribuidor, referido):
    c = Comision(date(2026, 11, 1), date(2026, 11, 30), 150, "Premium", Decimal("0.15"), distribuidor)
    c.agregar_pago_base(_pago(referido, "54.00"))
    assert c.calcular_monto() == Decimal("8.10")


def test_rn20_rechaza_pago_fallido_o_ya_comisionado(comision, referido):
    with pytest.raises(ReglaNegocioError):
        comision.agregar_pago_base(_pago(referido, estado=EstadoPago.FALLIDO))
    with pytest.raises(ReglaNegocioError):
        comision.agregar_pago_base(_pago(referido, comisionado=True))


def test_rn20_rechaza_pago_fuera_del_periodo(distribuidor, referido):
    c = Comision(date(2026, 11, 16), date(2026, 11, 30), 1, "Básico", Decimal("0.10"), distribuidor)
    pago = _pago(referido, dia=15)
    with pytest.raises(ReglaNegocioError):
        c.agregar_pago_base(pago)
    assert not pago.comisionado


def test_rn20_rechaza_pago_de_cliente_no_referido(comision, nuevo_cliente, nueva_suscripcion):
    ajeno = nueva_suscripcion(nuevo_cliente(correo="x@y.co", id=50), id=5)
    with pytest.raises(ReglaNegocioError):
        comision.agregar_pago_base(_pago(ajeno))


def test_rn20_comision_sin_pagos_vale_cero(comision):
    assert comision.calcular_monto() == Decimal("0.00")


def test_comision_validaciones_y_getters(distribuidor, comision):
    assert (comision.fecha_inicio, comision.fecha_fin, comision.clientes_referidos) == (
        date(2026, 11, 1),
        date(2026, 11, 30),
        1,
    )
    assert comision.nombre_categoria == "Básico" and comision.porcentaje == Decimal("0.10")
    assert comision.beneficiario is distribuidor and comision.cheque is None and "Básico" in repr(comision)
    args = (1, "Básico", Decimal("0.10"), distribuidor)
    with pytest.raises(ValidacionError):
        Comision(date(2026, 12, 1), date(2026, 11, 1), *args)
    with pytest.raises(ValidacionError):
        Comision(None, date(2026, 11, 1), *args)  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        Comision(date(2026, 11, 1), date(2026, 11, 2), -1, "Básico", Decimal("0.10"), distribuidor)
    with pytest.raises(ValidacionError):
        Comision(date(2026, 11, 1), date(2026, 11, 2), 1, "Básico", Decimal("0"), distribuidor)
    with pytest.raises(ValidacionError):
        Comision(date(2026, 11, 1), date(2026, 11, 2), 1, "Básico", Decimal("0.1"), None)  # type: ignore[arg-type]


# --- RN-21 cheque ------------------------------------------------------------------------------


def test_rn21_asociar_cheque_una_sola_vez(comision, referido):
    comision.agregar_pago_base(_pago(referido, "540.00"))
    cheque = Cheque("CHQ-2026-000007", "Andes Digital SAS (900123456)", Decimal("54.00"), date(2026, 12, 1))
    assert not comision.tiene_cheque()
    comision.asociar_cheque(cheque)
    assert comision.tiene_cheque() and comision.cheque is cheque
    with pytest.raises(ReglaNegocioError):
        comision.asociar_cheque(cheque)


def test_rn21_cheque_exige_pagos_y_monto_coincidente(comision, referido):
    cheque = Cheque("CHQ-2026-000007", "Andes", Decimal("54.00"), date(2026, 12, 1))
    with pytest.raises(ReglaNegocioError):
        comision.asociar_cheque(cheque)
    comision.agregar_pago_base(_pago(referido, "100.00"))
    with pytest.raises(ReglaNegocioError):
        comision.asociar_cheque(cheque)


@pytest.mark.parametrize("numero", ["CHQ-2026-7", "chq-2026-000007", "CHQ-26-000007", ""])
def test_rn21_formato_del_numero_de_cheque(numero):
    with pytest.raises(ValidacionError):
        Cheque(numero, "Andes", Decimal("1"), date(2026, 12, 1))


def test_rn21_cheque_validaciones_y_getters():
    c = Cheque("CHQ-2026-000007", "Andes", Decimal("54"), date(2026, 12, 1), id=3)
    assert (c.numero, c.beneficiario, c.monto, c.fecha_emision) == (
        "CHQ-2026-000007",
        "Andes",
        Decimal("54.00"),
        date(2026, 12, 1),
    )
    assert "CHQ" in repr(c)
    with pytest.raises(ValidacionError):
        Cheque("CHQ-2026-000007", "", Decimal("1"), date(2026, 12, 1))
    with pytest.raises(ValidacionError):
        Cheque("CHQ-2026-000007", "A", Decimal("0"), date(2026, 12, 1))
    with pytest.raises(ValidacionError):
        Cheque("CHQ-2026-000007", "A", Decimal("1"), None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("monto", "letras"),
    [
        ("54.00", "CINCUENTA Y CUATRO DÓLARES CON 00/100"),
        ("1.00", "UN DÓLAR CON 00/100"),
        ("0.50", "CERO DÓLARES CON 50/100"),
        ("21.05", "VEINTIÚN DÓLARES CON 05/100"),
        ("100.00", "CIEN DÓLARES CON 00/100"),
        ("101.00", "CIENTO UN DÓLARES CON 00/100"),
        ("16.99", "DIECISÉIS DÓLARES CON 99/100"),
        ("999.10", "NOVECIENTOS NOVENTA Y NUEVE DÓLARES CON 10/100"),
        ("1000.00", "MIL DÓLARES CON 00/100"),
        ("2531.00", "DOS MIL QUINIENTOS TREINTA Y UN DÓLARES CON 00/100"),
        ("21000.00", "VEINTIÚN MIL DÓLARES CON 00/100"),
        ("1000000.00", "UN MILLÓN DE DÓLARES CON 00/100"),
        ("2000001.00", "DOS MILLONES UN DÓLARES CON 00/100"),
        ("3000000.00", "TRES MILLONES DE DÓLARES CON 00/100"),
    ],
)
def test_rn21_monto_en_letras(monto, letras):
    assert Cheque("CHQ-2026-000001", "A", Decimal(monto), date(2026, 12, 1)).monto_en_letras() == letras
