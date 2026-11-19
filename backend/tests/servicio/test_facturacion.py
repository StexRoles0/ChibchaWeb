"""CU-FAC-01 cargar_pagos: RN-02 y RN-03 con repositorios en memoria."""

from datetime import date

import pytest

from chibchaweb.dominio.errores import ContingenciaActivaError, ErrorDominio
from chibchaweb.dominio.facturacion import EstadoPago

HOY = date(2026, 12, 1)


def test_rn03_cobro_exitoso_registra_el_pago_y_avanza_el_corte(
    facturacion, suscripciones, nuevo_cliente_con_suscripcion
):
    s = nuevo_cliente_con_suscripcion(corte=HOY)  # Oro Semestral, 54.00
    assert facturacion.cargar_pago(HOY) == 1
    (pago,) = suscripciones.pagos.values()
    assert (pago.estado, str(pago.monto)) == (EstadoPago.EXITOSO, "54.00") and pago.referencia_franquicia.startswith(
        "REF-"
    )
    assert s.fecha_corte == date(2027, 6, 1)  # +6 meses


def test_rn02_solo_se_cobran_las_vencidas(facturacion, suscripciones, nuevo_cliente_con_suscripcion):
    vencida = nuevo_cliente_con_suscripcion("a@correo.co", corte=date(2026, 11, 30))
    de_hoy = nuevo_cliente_con_suscripcion("b@correo.co", corte=HOY)  # fechaCorte ≤ fecha: vencida
    futura = nuevo_cliente_con_suscripcion("c@correo.co", corte=date(2026, 12, 2))
    assert facturacion.cargar_pago(HOY) == 2
    assert {p.suscripcion for p in suscripciones.pagos.values()} == {vencida, de_hoy}
    assert futura.fecha_corte == date(2026, 12, 2) and not futura.pagos


def test_rn02_el_servicio_vuelve_a_comprobar_la_vencida_y_la_activa(
    facturacion, suscripciones, nuevo_cliente_con_suscripcion, monkeypatch
):
    """Aunque el repositorio devuelva de más, no se cobra lo que no está vencido ni lo suspendido."""
    futura = nuevo_cliente_con_suscripcion("c@correo.co", corte=date(2026, 12, 2))
    suspendida = nuevo_cliente_con_suscripcion("d@correo.co", corte=HOY)
    suspendida.suspender()
    monkeypatch.setattr(suscripciones, "buscar_vencidas", lambda fecha: [futura, suspendida])
    assert facturacion.cargar_pago(HOY) == 0
    assert not suscripciones.pagos


def test_rn03_tarjeta_rechazada_queda_fallida_sin_mover_el_corte_y_el_lote_sigue(
    facturacion, suscripciones, nuevo_cliente_con_suscripcion
):
    mala = nuevo_cliente_con_suscripcion("mala@correo.co", numero="4111111111110341", corte=HOY)  # termina en 0341
    buena = nuevo_cliente_con_suscripcion("buena@correo.co", corte=HOY)
    assert facturacion.cargar_pago(HOY) == 2  # cuenta exitosos y fallidos
    assert [p.estado for p in mala.pagos] == [EstadoPago.FALLIDO] and mala.pagos[0].referencia_franquicia is None
    assert mala.fecha_corte == HOY
    assert [p.estado for p in buena.pagos] == [EstadoPago.EXITOSO] and buena.fecha_corte == date(2027, 6, 1)
    assert len(suscripciones.pagos) == 2  # el fallido también se registra


def test_rn03_excepcion_de_la_pasarela_es_un_pago_fallido(
    facturacion, pasarela, suscripciones, nuevo_cliente_con_suscripcion, monkeypatch
):
    def caida(medio, monto):
        raise ConnectionError("pasarela caída")

    monkeypatch.setattr(pasarela, "cobrar", caida)
    s = nuevo_cliente_con_suscripcion(corte=HOY)
    assert facturacion.cargar_pago(HOY) == 1
    assert s.pagos[0].estado is EstadoPago.FALLIDO and s.fecha_corte == HOY


def test_rn03_tarjeta_vencida_es_un_pago_fallido_sin_llamar_a_la_pasarela(
    facturacion, pasarela, nuevo_cliente_con_suscripcion
):
    s = nuevo_cliente_con_suscripcion(vencimiento=date(2020, 1, 1), corte=HOY)
    assert facturacion.cargar_pago(HOY) == 1
    assert s.pagos[0].estado is EstadoPago.FALLIDO and s.fecha_corte == HOY and not pasarela.cobros


def test_sin_vencidas_no_procesa_nada(facturacion, nuevo_cliente_con_suscripcion):
    nuevo_cliente_con_suscripcion(corte=date(2027, 1, 1))
    assert facturacion.cargar_pago(HOY) == 0


def test_contingencia_al_registrar_el_pago_detiene_el_lote(facturacion, suscripciones, nuevo_cliente_con_suscripcion):
    nuevo_cliente_con_suscripcion("a@correo.co", corte=HOY)
    nuevo_cliente_con_suscripcion("b@correo.co", corte=HOY)
    suscripciones.fallar_con = ContingenciaActivaError("BD caída; evento respaldado.")
    with pytest.raises(ContingenciaActivaError, match="tras 0 cobros"):
        facturacion.cargar_pago(HOY)
    assert not suscripciones.pagos  # no siguió con la segunda: la siguiente corrida no cobraría dos veces


def test_contingencia_a_mitad_del_lote_informa_cuantos_alcanzo(
    facturacion, suscripciones, nuevo_cliente_con_suscripcion, monkeypatch
):
    nuevo_cliente_con_suscripcion("a@correo.co", corte=HOY)
    nuevo_cliente_con_suscripcion("b@correo.co", corte=HOY)
    original = suscripciones.registrar_pago
    llamadas = []

    def segunda_falla(pago):
        llamadas.append(pago)
        if len(llamadas) == 2:
            raise ContingenciaActivaError("BD caída.")
        original(pago)

    monkeypatch.setattr(suscripciones, "registrar_pago", segunda_falla)
    with pytest.raises(ContingenciaActivaError, match="tras 1 cobros"):
        facturacion.cargar_pago(HOY)
    assert len(suscripciones.pagos) == 1


def test_un_error_del_dominio_en_una_suscripcion_no_frena_las_demas(
    facturacion, suscripciones, nuevo_cliente_con_suscripcion, monkeypatch
):
    nuevo_cliente_con_suscripcion("a@correo.co", corte=HOY)
    nuevo_cliente_con_suscripcion("b@correo.co", corte=HOY)
    original = suscripciones.registrar_pago
    llamadas = []

    def primera_falla(pago):
        llamadas.append(pago)
        if len(llamadas) == 1:
            raise ErrorDominio("dato inválido")
        original(pago)

    monkeypatch.setattr(suscripciones, "registrar_pago", primera_falla)
    assert facturacion.cargar_pago(HOY) == 1
    assert len(suscripciones.pagos) == 1
