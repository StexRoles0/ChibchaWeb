"""CU-FAC-01 ``cargar_pagos [--fecha]`` (D-09): RN-02 y RN-03 contra PostgreSQL, y la contingencia (RT04)."""

from datetime import date
from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError
from freezegun import freeze_time

from chibchaweb.dominio.facturacion import EstadoPago
from config.contenedor import contenedor
from tests.web.conftest import cliente_en_sesion as _registrar


def cliente_en_sesion(correo, **cambios):
    return _registrar(correo, sitio=correo.split("@")[0], **cambios)


CORTE = date(2026, 12, 1)  # corte de los registros nuevos (RN-04)


def correr(*args) -> str:
    salida = StringIO()
    call_command("cargar_pagos", *args, stdout=salida)
    return salida.getvalue()


def suscripcion_de(http):
    (s,) = contenedor().usuarios.buscar_por_id(http.id_usuario).suscripciones
    return contenedor().suscripciones.buscar_por_id(s.id)


def test_rn03_cobra_las_vencidas_registra_el_pago_exitoso_y_avanza_el_corte():
    http = cliente_en_sesion("pagador@correo.co")  # Oro Semestral = 54.00
    assert correr("--fecha", "2026-12-01") == "cargar_pagos 2026-12-01: 1 cobros procesados\n"
    s = suscripcion_de(http)
    (pago,) = s.pagos
    assert (pago.estado, str(pago.monto)) == (EstadoPago.EXITOSO, "54.00")
    assert pago.referencia_franquicia.startswith("REF-") and not pago.comisionado
    assert s.fecha_corte == date(2027, 6, 1)  # +6 meses


def test_sin_fecha_usa_hoy():
    http = cliente_en_sesion("pagador@correo.co")
    assert "2026-12-01: 1 cobros procesados" in correr()
    assert len(suscripcion_de(http).pagos) == 1


def test_rn02_una_suscripcion_no_vencida_no_se_cobra():
    http = cliente_en_sesion("pagador@correo.co")
    assert "2026-11-30: 0 cobros procesados" in correr("--fecha", "2026-11-30")
    assert suscripcion_de(http).pagos == () and suscripcion_de(http).fecha_corte == CORTE


def test_correr_dos_veces_el_mismo_dia_no_cobra_dos_veces():
    http = cliente_en_sesion("pagador@correo.co")
    correr()
    assert "0 cobros procesados" in correr()
    assert len(suscripcion_de(http).pagos) == 1


def test_rn03_tarjeta_rechazada_queda_fallida_sin_mover_el_corte_y_el_lote_sigue():
    mala = cliente_en_sesion("mala@correo.co", numeroTarjeta="4111111111110341")  # la pasarela rechaza ...0341
    buena = cliente_en_sesion("buena@correo.co")
    assert "2 cobros procesados" in correr()
    s_mala, s_buena = suscripcion_de(mala), suscripcion_de(buena)
    assert [p.estado for p in s_mala.pagos] == [EstadoPago.FALLIDO] and s_mala.fecha_corte == CORTE
    assert s_mala.pagos[0].referencia_franquicia is None
    assert [p.estado for p in s_buena.pagos] == [EstadoPago.EXITOSO] and s_buena.fecha_corte == date(2027, 6, 1)


def test_rn03_tarjeta_vencida_es_un_pago_fallido():
    http = cliente_en_sesion("vencida@correo.co", vencimiento="2026-12-01")  # vigente hoy
    with freeze_time("2027-02-01"):  # cuando el cobro llega, la tarjeta ya venció
        assert "1 cobros procesados" in correr("--fecha", "2027-02-01")
    s = suscripcion_de(http)
    assert [p.estado for p in s.pagos] == [EstadoPago.FALLIDO] and s.fecha_corte == CORTE


def test_fecha_con_formato_invalido_es_un_error():
    with pytest.raises(CommandError, match="AAAA-MM-DD"):
        correr("--fecha", "01/12/2026")


def test_con_eventos_pendientes_en_el_respaldo_la_tarea_no_corre():
    http = cliente_en_sesion("pagador@correo.co")
    contenedor().gestor.respaldar("Usuario.actualizar", "{}")
    with pytest.raises(CommandError, match="1 eventos pendientes"):
        correr()
    assert suscripcion_de(http).pagos == ()


def test_rt04_si_la_bd_cae_el_lote_se_detiene_y_tras_sincronizar_no_se_cobra_dos_veces():
    primero = cliente_en_sesion("primero@correo.co")
    segundo = cliente_en_sesion("segundo@correo.co")
    with (
        mock.patch(
            "chibchaweb.persistencia.mapeadores.suscripcion.PagoOrm.save", side_effect=OperationalError("sin BD")
        ),
        pytest.raises(CommandError, match="Contingencia activa.*tras 0 cobros"),
    ):
        correr()
    eventos = contenedor().gestor.recuperar_pendientes()
    assert len(eventos) == 1 and eventos[0].startswith("Suscripcion.registrar_pago|")  # se detuvo: solo un evento
    assert '"fecha_corte":"2027-06-01"' in eventos[0]  # el corte viaja con el pago
    assert suscripcion_de(primero).pagos == () and suscripcion_de(segundo).pagos == ()
    with pytest.raises(CommandError, match="pendientes"):  # mientras no se sincronice, la tarea no corre
        correr()

    assert contenedor().servicio_contingencia.sincronizar_respaldo() == 1
    cobrada = [s for s in (suscripcion_de(primero), suscripcion_de(segundo)) if s.pagos]
    assert len(cobrada) == 1 and cobrada[0].fecha_corte == date(2027, 6, 1)  # pago y corte quedaron juntos
    assert "1 cobros procesados" in correr()  # solo falta la otra: la ya cobrada no se vuelve a cobrar
    assert all(len(suscripcion_de(h).pagos) == 1 for h in (primero, segundo))
