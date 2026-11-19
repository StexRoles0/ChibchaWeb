"""CU-COM-01 calcular_comisiones y CU-COM-02 generar_cheques: RN-19, RN-20 y RN-21 con repositorios en memoria."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from freezegun import freeze_time

from chibchaweb.dominio._comun import ZONA
from chibchaweb.dominio.cuentas import Cliente, Direccion, TarjetaCredito
from chibchaweb.dominio.errores import ContingenciaActivaError, NoEncontradoError, ReglaNegocioError, ValidacionError
from chibchaweb.dominio.facturacion import EstadoPago, Pago
from chibchaweb.servicio.dto import ResumenDTO

INICIO, FIN = date(2026, 11, 1), date(2026, 11, 30)


def pagar(suscripcion, monto="54.00", dia=15, estado=EstadoPago.EXITOSO, mes=11, comisionado=False):
    pago = Pago(
        Decimal(monto),
        estado,
        suscripcion,
        fecha=datetime(2026, mes, dia, 10, 0, tzinfo=ZONA),
        referencia_franquicia="REF-1" if estado is EstadoPago.EXITOSO else None,
        comisionado=comisionado,
    )
    suscripcion.agregar_pago(pago)
    return pago


@pytest.fixture
def referido(nuevo_cliente_con_suscripcion, distribuidor):
    return nuevo_cliente_con_suscripcion(distribuidor=distribuidor)


def agregar_referidos_sin_pagos(distribuidor, cantidad, desde=0):
    for i in range(desde, desde + cantidad):
        c = Cliente(
            f"Cliente {i}",
            f"c{i}@correo.co",
            "3000000000",
            Direccion("Calle 1", "Cali", "760001"),
            Direccion("Calle 2", "Cali", "760002"),
            TarjetaCredito("4111111111111111", date(2099, 1, 1), _visa()),
            id=10_000 + i,
        )
        distribuidor.agregar_referido(c)


def _visa():
    from tests.falsos import franquicias_estandar

    return franquicias_estandar()[0]


# --- CU-COM-01 ---------------------------------------------------------------------------------
def test_rn20_crea_una_comision_por_distribuidor_con_pagos_y_los_marca_comisionados(
    servicio_comisiones, comisiones, referido, distribuidor
):
    p1, p2 = pagar(referido, "54.00", 10), pagar(referido, "10.00", 20)
    assert servicio_comisiones.calcular_comision(INICIO, FIN) == 1
    (c,) = comisiones.objetos.values()
    assert c.beneficiario is distribuidor and (c.fecha_inicio, c.fecha_fin) == (INICIO, FIN)
    assert c.pagos_base == (p1, p2) and p1.comisionado and p2.comisionado
    assert c.calcular_monto() == Decimal("6.40")  # (54 + 10) × 10 %
    assert c.clientes_referidos == 1 and not c.tiene_cheque() and distribuidor.comisiones == (c,)


def test_rn19_categoria_basica_con_100_referidos_y_premium_con_101(
    servicio_comisiones, comisiones, referido, distribuidor
):
    agregar_referidos_sin_pagos(distribuidor, 99)  # + el referido real = 100
    pagar(referido, "100.00")
    servicio_comisiones.calcular_comision(INICIO, FIN)
    basica = next(iter(comisiones.objetos.values()))
    assert (basica.nombre_categoria, basica.porcentaje, basica.clientes_referidos) == ("Básico", Decimal("0.10"), 100)
    assert basica.calcular_monto() == Decimal("10.00")

    comisiones.objetos.clear()
    pagar(referido, "100.00", dia=16)  # otro pago, distinto del anterior ya comisionado
    agregar_referidos_sin_pagos(distribuidor, 1, desde=99)  # 101
    servicio_comisiones.calcular_comision(INICIO, FIN)
    premium = next(iter(comisiones.objetos.values()))
    assert (premium.nombre_categoria, premium.porcentaje, premium.clientes_referidos) == (
        "Premium",
        Decimal("0.15"),
        101,
    )
    assert premium.calcular_monto() == Decimal("15.00")


def test_rn20_distribuidor_sin_pagos_no_genera_comision(servicio_comisiones, comisiones, referido):
    assert servicio_comisiones.calcular_comision(INICIO, FIN) == 0
    assert not comisiones.objetos


def test_rn20_solo_pagos_exitosos_sin_comisionar_y_dentro_del_periodo(servicio_comisiones, comisiones, referido):
    valido = pagar(referido, "54.00", 15)
    pagar(referido, "54.00", 16, estado=EstadoPago.FALLIDO)
    pagar(referido, "54.00", 17, comisionado=True)
    pagar(referido, "54.00", 18, mes=10)  # fuera del periodo
    pagar(referido, "54.00", 1, mes=12)
    assert servicio_comisiones.calcular_comision(INICIO, FIN) == 1
    (c,) = comisiones.objetos.values()
    assert c.pagos_base == (valido,)


def test_rn20_los_limites_del_periodo_son_inclusivos(servicio_comisiones, comisiones, referido):
    primero, ultimo = pagar(referido, "10.00", 1), pagar(referido, "10.00", 30)
    servicio_comisiones.calcular_comision(INICIO, FIN)
    (c,) = comisiones.objetos.values()
    assert set(c.pagos_base) == {primero, ultimo}


def test_rn20_los_pagos_de_clientes_sin_distribuidor_no_comisionan(
    servicio_comisiones, comisiones, nuevo_cliente_con_suscripcion, distribuidor
):
    pagar(nuevo_cliente_con_suscripcion("libre@correo.co"))
    assert servicio_comisiones.calcular_comision(INICIO, FIN) == 0


def test_rn20_varios_distribuidores_cada_uno_con_su_comision(
    servicio_comisiones, comisiones, usuarios, referido, nuevo_cliente_con_suscripcion, distribuidor
):
    from chibchaweb.dominio.cuentas import Distribuidor

    otro = Distribuidor("Otro", "otro@d.co", "6015550000", "900555", "DIS-OTRO01")
    usuarios.insertar(otro)
    pagar(referido)
    pagar(nuevo_cliente_con_suscripcion("x@correo.co", distribuidor=otro), "20.00")
    assert servicio_comisiones.calcular_comision(INICIO, FIN) == 2
    assert {c.beneficiario for c in comisiones.objetos.values()} == {distribuidor, otro}


def test_calcular_dos_veces_el_mismo_periodo_no_duplica(servicio_comisiones, comisiones, referido):
    pagar(referido)
    assert servicio_comisiones.calcular_comision(INICIO, FIN) == 1
    assert servicio_comisiones.calcular_comision(INICIO, FIN) == 0
    assert len(comisiones.objetos) == 1


def test_periodo_invalido_es_422(servicio_comisiones):
    with pytest.raises(ValidacionError) as error:
        servicio_comisiones.calcular_comision(FIN, INICIO)
    assert error.value.campo == "fechaFin"
    with pytest.raises(ValidacionError):
        servicio_comisiones.calcular_comision(None, FIN)


def test_contingencia_detiene_el_calculo(servicio_comisiones, comisiones, referido):
    pagar(referido)
    comisiones.fallar_con = ContingenciaActivaError("BD caída; evento respaldado.")
    with pytest.raises(ContingenciaActivaError):
        servicio_comisiones.calcular_comision(INICIO, FIN)


# --- CU-COM-02 ---------------------------------------------------------------------------------
@pytest.fixture
def comision_id(servicio_comisiones, comisiones, referido):
    pagar(referido, "54.00")
    servicio_comisiones.calcular_comision(INICIO, FIN)
    return next(iter(comisiones.objetos))


@freeze_time("2026-12-01 03:30:00-05:00")
def test_rn21_genera_el_cheque_con_numero_beneficiario_y_monto(
    servicio_comisiones, comisiones, comision_id, distribuidor
):
    servicio_comisiones.generar_cheque(comision_id)
    c = comisiones.buscar_por_id(comision_id)
    assert c.tiene_cheque() and comisiones.cheques_registrados == [comision_id]
    assert c.cheque.numero == f"CHQ-2026-{comision_id:06d}"
    assert c.cheque.beneficiario == "Andes Digital - 900123456"  # nombre y documento del distribuidor
    assert c.cheque.monto == Decimal("5.40") and c.cheque.fecha_emision == date(2026, 12, 1)
    assert c.cheque.monto_en_letras() == "CINCO DÓLARES CON 40/100"


@freeze_time("2026-12-01")
def test_rn21_una_comision_con_cheque_no_se_puede_volver_a_emitir(servicio_comisiones, comisiones, comision_id):
    servicio_comisiones.generar_cheque(comision_id)
    with pytest.raises(ReglaNegocioError):
        servicio_comisiones.generar_cheque(comision_id)
    assert comisiones.cheques_registrados == [comision_id]  # una sola vez


def test_generar_cheque_de_una_comision_inexistente_es_404(servicio_comisiones):
    with pytest.raises(NoEncontradoError):
        servicio_comisiones.generar_cheque(999)


@freeze_time("2026-12-01")
def test_el_beneficiario_larguisimo_se_recorta_para_caber_en_el_cheque(
    servicio_comisiones, comisiones, comision_id, distribuidor
):
    distribuidor.nombre = "N" * 120
    servicio_comisiones.generar_cheque(comision_id)
    beneficiario = comisiones.buscar_por_id(comision_id).cheque.beneficiario
    assert len(beneficiario) == 120 and beneficiario.endswith(" - 900123456")


@freeze_time("2026-12-01")
def test_contingencia_al_registrar_el_cheque_se_propaga(servicio_comisiones, comisiones, comision_id):
    comisiones.fallar_con = ContingenciaActivaError("BD caída.")
    with pytest.raises(ContingenciaActivaError):
        servicio_comisiones.generar_cheque(comision_id)


@freeze_time("2026-12-01")
def test_p08_consultar_comisiones_sin_cheque(servicio_comisiones, comisiones, comision_id):
    (fila,) = servicio_comisiones.consultar_comisiones_sin_cheque()
    assert isinstance(fila, ResumenDTO) and fila.id == comision_id and fila.estado == "SIN_CHEQUE"
    assert "Andes Digital" in fila.titulo and "2026-11-01 a 2026-11-30" in fila.subtitulo and "5.40" in fila.subtitulo
    servicio_comisiones.generar_cheque(comision_id)
    assert servicio_comisiones.consultar_comisiones_sin_cheque() == []


def test_las_categorias_son_obligatorias(comisiones, usuarios, suscripciones):
    from chibchaweb.servicio.servicios import ServicioComisiones

    with pytest.raises(ValidacionError):
        ServicioComisiones([], comisiones, usuarios, suscripciones)
