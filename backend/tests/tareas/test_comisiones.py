"""CU-COM-01 ``calcular_comisiones [--inicio --fin]`` y CU-COM-02 ``generar_cheques`` (D-09): RN-19, RN-20 y RN-21."""

from datetime import date
from decimal import Decimal
from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError
from freezegun import freeze_time

from chibchaweb.servicio.errores import ReglaNegocioError
from config.contenedor import contenedor
from tests.web.conftest import cliente_en_sesion as _registrar

PERIODO = ("--inicio", "2026-12-01", "--fin", "2026-12-31")


def registrar(correo, **cambios):
    return _registrar(correo, sitio=correo.split("@")[0], **cambios)


def correr(comando, *args) -> str:
    salida = StringIO()
    call_command(comando, *args, stdout=salida, stderr=StringIO())
    return salida.getvalue()


def comisiones():
    return contenedor().comisiones.buscar_por_filtro("")


@pytest.fixture
def referido():
    """Cliente referido por DIS-ANDES1 (seed) con un pago exitoso de 54.00 hoy."""
    http = registrar("referido@correo.co", codigoDistribuidor="DIS-ANDES1")
    correr("cargar_pagos")
    return http


# --- calcular_comisiones -----------------------------------------------------------------------
def test_rn20_crea_la_comision_del_periodo_y_marca_los_pagos(referido):
    assert (
        correr("calcular_comisiones", *PERIODO) == "calcular_comisiones 2026-12-01 a 2026-12-31: 1 comisiones creadas\n"
    )
    (c,) = comisiones()
    assert c.beneficiario.codigo == "DIS-ANDES1" and (c.fecha_inicio, c.fecha_fin) == (
        date(2026, 12, 1),
        date(2026, 12, 31),
    )
    assert (c.nombre_categoria, c.porcentaje, c.clientes_referidos) == ("Básico", Decimal("0.10"), 1)  # RN-19
    (pago,) = c.pagos_base
    assert pago.comisionado and c.calcular_monto() == Decimal("5.40") and not c.tiene_cheque()


def test_calcular_dos_veces_no_duplica_las_comisiones(referido):
    correr("calcular_comisiones", *PERIODO)
    assert "0 comisiones creadas" in correr("calcular_comisiones", *PERIODO)
    assert len(comisiones()) == 1


def test_rn20_sin_pagos_en_el_periodo_no_se_crea_comision(referido):
    assert "0 comisiones creadas" in correr("calcular_comisiones", "--inicio", "2026-11-01", "--fin", "2026-11-30")
    assert comisiones() == []


def test_rn20_los_clientes_sin_distribuidor_no_comisionan():
    registrar("libre@correo.co")
    correr("cargar_pagos")
    assert "0 comisiones creadas" in correr("calcular_comisiones", *PERIODO)


def test_sin_argumentos_calcula_el_mes_anterior(referido):
    assert "2026-11-01 a 2026-11-30: 0 comisiones creadas" in correr("calcular_comisiones")  # hoy es 1-dic-2026
    with freeze_time("2027-01-01 03:00:00-05:00"):  # el cron del 1 de enero liquida diciembre
        assert "2026-12-01 a 2026-12-31: 1 comisiones creadas" in correr("calcular_comisiones")


def test_inicio_y_fin_van_juntos():
    for argumentos in (("--inicio", "2026-12-01"), ("--fin", "2026-12-31")):
        with pytest.raises(CommandError, match="juntos"):
            correr("calcular_comisiones", *argumentos)


def test_periodo_invertido_es_un_error():
    with pytest.raises(CommandError, match="fecha fin"):
        correr("calcular_comisiones", "--inicio", "2026-12-31", "--fin", "2026-12-01")


def test_fecha_con_formato_invalido_es_un_error():
    with pytest.raises(CommandError, match="AAAA-MM-DD"):
        correr("calcular_comisiones", "--inicio", "ayer", "--fin", "hoy")


def test_con_eventos_pendientes_en_el_respaldo_no_corre(referido):
    contenedor().gestor.respaldar("Usuario.actualizar", "{}")
    with pytest.raises(CommandError, match="pendientes"):
        correr("calcular_comisiones", *PERIODO)
    assert comisiones() == []


def test_rt04_si_la_bd_cae_el_calculo_se_detiene_y_respalda_la_comision(referido):
    with (
        mock.patch(
            "chibchaweb.persistencia.mapeadores.comision.ComisionOrm.save", side_effect=OperationalError("sin BD")
        ),
        pytest.raises(CommandError, match="Contingencia activa"),
    ):
        correr("calcular_comisiones", *PERIODO)
    assert comisiones() == []
    (evento,) = contenedor().gestor.recuperar_pendientes()
    assert evento.startswith("Comision.insertar|")
    assert contenedor().servicio_contingencia.sincronizar_respaldo() == 1
    (c,) = comisiones()
    assert c.pagos_base[0].comisionado and "0 comisiones creadas" in correr("calcular_comisiones", *PERIODO)


# --- generar_cheques ---------------------------------------------------------------------------
@pytest.fixture
def comision(referido):
    correr("calcular_comisiones", *PERIODO)
    return comisiones()[0]


def test_rn21_genera_el_cheque_de_cada_comision_sin_cheque(comision):
    assert correr("generar_cheques") == "generar_cheques: 1 cheques generados de 1 comisiones sin cheque\n"
    (c,) = comisiones()
    assert c.cheque.numero == f"CHQ-2026-{comision.id:06d}"
    assert c.cheque.beneficiario == "Andes Digital SAS - 900123456"
    assert c.cheque.monto == Decimal("5.40") and c.cheque.fecha_emision == date(2026, 12, 1)
    assert c.cheque.monto_en_letras() == "CINCO DÓLARES CON 40/100"


def test_generar_dos_veces_no_emite_otro_cheque(comision):
    correr("generar_cheques")
    assert "0 cheques generados de 0 comisiones" in correr("generar_cheques")
    assert comisiones()[0].cheque.id is not None and len(comisiones()) == 1


def test_sin_comisiones_no_hace_nada():
    assert "0 cheques generados de 0 comisiones" in correr("generar_cheques")


def test_p08_una_comision_con_error_no_frena_las_demas_pero_el_comando_falla(comision):
    servicio = contenedor().servicio_comisiones
    with (
        mock.patch.object(servicio, "generar_cheque", side_effect=ReglaNegocioError("ya tiene cheque")),
        pytest.raises(CommandError, match="1 comisiones sin cheque por error.*ya tiene cheque"),
    ):
        correr("generar_cheques")


def test_con_eventos_pendientes_en_el_respaldo_no_genera_cheques(comision):
    contenedor().gestor.respaldar("Usuario.actualizar", "{}")
    with pytest.raises(CommandError, match="pendientes"):
        correr("generar_cheques")
    assert not comisiones()[0].tiene_cheque()


def test_rt04_si_la_bd_cae_al_emitir_el_cheque_se_detiene_y_respalda_el_evento(comision):
    with (
        mock.patch(
            "chibchaweb.persistencia.mapeadores.comision.ChequeOrm.save", side_effect=OperationalError("sin BD")
        ),
        pytest.raises(CommandError, match="Contingencia activa tras 0 cheques"),
    ):
        correr("generar_cheques")
    (evento,) = contenedor().gestor.recuperar_pendientes()
    assert evento.startswith("Comision.registrar_cheque|")
    assert contenedor().servicio_contingencia.sincronizar_respaldo() == 1
    assert comisiones()[0].tiene_cheque() and "0 cheques generados de 0" in correr("generar_cheques")
