"""Hospedaje y cobro: RN-01 a RN-04 y RN-14."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time

from chibchaweb.dominio.errores import EstadoInvalidoError, ReglaNegocioError, ValidacionError
from chibchaweb.dominio.facturacion import EstadoPago, Pago
from chibchaweb.dominio.hospedaje import PaqueteHosting, PlanPago, Plataforma, SitioWeb, Suscripcion
from tests.dominio.conftest import VISA_RECHAZADA_PASARELA
from tests.falsos import PasarelaPagoFalsa

# --- RN-01 monto del periodo -------------------------------------------------------------------


def test_rn01_monto_oro_semestral_es_54(catalogo):
    oro, semestral = catalogo.buscar_paquete(2), catalogo.buscar_plan(3)
    assert oro.calcular_monto(semestral) == Decimal("54.00")


@pytest.mark.parametrize(
    ("paquete", "plan", "esperado"),
    [
        (1, 1, "5.00"),
        (1, 2, "14.25"),
        (1, 4, "51.00"),
        (2, 2, "28.50"),
        (3, 3, "108.00"),
        (3, 4, "204.00"),
    ],
)
def test_rn01_tabla_de_montos(catalogo, paquete, plan, esperado):
    resultado = catalogo.buscar_paquete(paquete).calcular_monto(catalogo.buscar_plan(plan))
    assert resultado == Decimal(esperado) and isinstance(resultado, Decimal)


def test_rn01_redondeo_half_up():
    plan = PlanPago("Raro", 1, Decimal("0.125"))
    assert PaqueteHosting("X", Decimal("0.10")).calcular_monto(plan) == Decimal("0.09")  # 0.0875 → 0.09
    assert plan.aplicar_descuento(Decimal("1.00")) == Decimal("0.88")  # 0.875 → 0.88


def test_rn01_monto_del_periodo_delega_en_paquete(cliente, nueva_suscripcion):
    assert nueva_suscripcion(cliente).monto_del_periodo() == Decimal("54.00")


def test_rn01_rechaza_float_y_valores_fuera_de_rango():
    with pytest.raises(ValidacionError):
        PaqueteHosting("X", 5.0)  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        PaqueteHosting("X", Decimal("0"))
    with pytest.raises(ValidacionError):
        PaqueteHosting("X", "abc")  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        PlanPago("X", 0, Decimal("0"))
    with pytest.raises(ValidacionError):
        PlanPago("X", 1, Decimal("1.5"))


def test_catalogo_getters(catalogo):
    oro, anual = catalogo.buscar_paquete(2), catalogo.buscar_plan(4)
    assert (oro.nombre, oro.tarifa_mensual, oro.descripcion) == ("Chibcha-Oro", Decimal("10.00"), "Paquete intermedio")
    assert (anual.nombre, anual.meses, anual.descuento) == ("Anual", 12, Decimal("0.15"))
    assert "Oro" in repr(oro) and "Anual" in repr(anual)


# --- RN-02 vencimiento -------------------------------------------------------------------------


def test_rn02_vencida_si_corte_menor_o_igual_a_fecha(cliente, nueva_suscripcion):
    s = nueva_suscripcion(cliente, fecha_inicio=date(2026, 11, 16))
    assert s.esta_vencida(date(2026, 11, 16)) is True
    assert s.esta_vencida(date(2026, 11, 17)) is True
    assert s.esta_vencida(date(2026, 11, 15)) is False


# --- RN-03 cobro --------------------------------------------------------------------------------


@freeze_time("2026-11-16 15:00:00")
def test_rn03_cobro_exitoso_crea_pago_con_referencia_y_avanza_corte(cliente, nueva_suscripcion):
    s = nueva_suscripcion(cliente, plan_id=3)
    pasarela = PasarelaPagoFalsa()
    pago = s.cobrar(pasarela)
    assert pago.estado is EstadoPago.EXITOSO and pago.referencia_franquicia.startswith("REF-")
    assert pago.monto == Decimal("54.00") and pago.suscripcion is s
    assert s.pagos == (pago,)
    assert s.fecha_corte == date(2027, 5, 16)
    assert pasarela.cobros == [(cliente.medio_pago, Decimal("54.00"))]


@freeze_time("2026-11-16 15:00:00")
def test_rn03_cobro_fallido_no_mueve_el_corte(nuevo_cliente, nueva_tarjeta, nueva_suscripcion):
    c = nuevo_cliente(tarjeta=nueva_tarjeta(numero=VISA_RECHAZADA_PASARELA), id=1)
    s = nueva_suscripcion(c)
    pago = s.cobrar(PasarelaPagoFalsa())
    assert pago.estado is EstadoPago.FALLIDO and pago.referencia_franquicia is None
    assert s.fecha_corte == date(2026, 11, 16) and s.pagos == (pago,)


@freeze_time("2026-11-16 15:00:00")
def test_rn03_excepcion_de_la_pasarela_es_pago_fallido(cliente, nueva_suscripcion):
    class PasarelaCaida(PasarelaPagoFalsa):
        def cobrar(self, medio, monto):
            raise ConnectionError("sin red")

    pago = nueva_suscripcion(cliente).cobrar(PasarelaCaida())
    assert pago.estado is EstadoPago.FALLIDO


@freeze_time("2026-11-16 15:00:00")
def test_rn03_tarjeta_vencida_no_se_envia_a_la_pasarela(nuevo_cliente, nueva_tarjeta, nueva_suscripcion):
    c = nuevo_cliente(tarjeta=nueva_tarjeta(vencimiento=date(2026, 1, 1)), id=1)
    pasarela = PasarelaPagoFalsa()
    pago = nueva_suscripcion(c).cobrar(pasarela)
    assert pago.estado is EstadoPago.FALLIDO and pasarela.cobros == []


@freeze_time("2026-11-16 15:00:00")
def test_rn03_un_fallido_no_detiene_el_lote(nuevo_cliente, nueva_tarjeta, nueva_suscripcion):
    rechazada = nuevo_cliente(correo="r@x.co", tarjeta=nueva_tarjeta(numero=VISA_RECHAZADA_PASARELA), id=1)
    buena = nuevo_cliente(correo="b@x.co", id=2)
    lote = [nueva_suscripcion(rechazada, sitio="r"), nueva_suscripcion(buena, sitio="b")]
    pasarela = PasarelaPagoFalsa()
    estados = [s.cobrar(pasarela).estado for s in lote]
    assert estados == [EstadoPago.FALLIDO, EstadoPago.EXITOSO]


def test_rn03_suscripcion_inactiva_no_se_cobra_ni_cambia(cliente, nueva_suscripcion, catalogo):
    s = nueva_suscripcion(cliente)
    s.suspender()
    with pytest.raises(EstadoInvalidoError):
        s.cobrar(PasarelaPagoFalsa())
    with pytest.raises(EstadoInvalidoError):
        s.cambiar_plan(catalogo.buscar_plan(1))
    with pytest.raises(EstadoInvalidoError):
        s.cambiar_paquete(catalogo.buscar_paquete(1))


@pytest.mark.parametrize(
    ("inicio", "meses", "esperado"),
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2026, 11, 30), 3, date(2027, 2, 28)),
        (date(2027, 12, 15), 12, date(2028, 12, 15)),
        (date(2028, 1, 31), 1, date(2028, 2, 29)),
    ],
)
def test_rn03_avanzar_corte_suma_meses_del_plan(cliente, catalogo, inicio, meses, esperado):
    plan = next(p for p in catalogo.listar_planes() if p.meses == meses)
    s = Suscripcion(cliente, SitioWeb("a.chibchaweb.co", Plataforma.UNIX), catalogo.buscar_paquete(1), plan, inicio)
    s.avanzar_corte()
    assert s.fecha_corte == esperado


# --- RN-04 alta de la suscripción ---------------------------------------------------------------


def test_rn04_nueva_suscripcion_inicia_y_corta_hoy(cliente, nueva_suscripcion):
    s = nueva_suscripcion(cliente, fecha_inicio=date(2026, 11, 16))
    assert s.fecha_inicio == s.fecha_corte == date(2026, 11, 16)
    assert s.activa is True and s.titular is cliente


def test_suscripcion_validaciones(cliente, catalogo):
    sitio = SitioWeb("a.chibchaweb.co", Plataforma.UNIX)
    paquete, plan = catalogo.buscar_paquete(1), catalogo.buscar_plan(1)
    with pytest.raises(ValidacionError):
        Suscripcion(cliente, sitio, None, plan, date(2026, 1, 1))  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        Suscripcion(cliente, sitio, paquete, plan, None)  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        Suscripcion(cliente, sitio, paquete, plan, date(2026, 2, 1), fecha_corte=date(2026, 1, 1))


def test_cambiar_paquete_y_plan(cliente, nueva_suscripcion, catalogo):
    s = nueva_suscripcion(cliente)
    s.cambiar_paquete(catalogo.buscar_paquete(3))
    s.cambiar_plan(catalogo.buscar_plan(4))
    assert s.paquete.nombre == "Chibcha-Platino" and s.plan.nombre == "Anual"
    assert s.monto_del_periodo() == Decimal("204.00")
    with pytest.raises(ValidacionError):
        s.cambiar_plan(None)  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        s.cambiar_paquete(None)  # type: ignore[arg-type]
    assert "Suscripcion" in repr(s) and s.sitio.subdominio == "tiendalaura.chibchaweb.co"


def test_agregar_pago_de_otra_suscripcion_falla(cliente, nueva_suscripcion):
    s1, s2 = nueva_suscripcion(cliente, sitio="a", id=1), nueva_suscripcion(cliente, sitio="b", id=2)
    pago = Pago(Decimal("5"), EstadoPago.EXITOSO, s2, referencia_franquicia="R1")
    with pytest.raises(ReglaNegocioError):
        s1.agregar_pago(pago)
    s2.agregar_pago(pago)
    s2.agregar_pago(pago)
    assert s2.pagos == (pago,)


# --- RN-14 sitio web ---------------------------------------------------------------------------


@pytest.mark.parametrize("plataforma", [Plataforma.WINDOWS, Plataforma.UNIX])
def test_rn14_sitio_con_subdominio_y_plataforma(plataforma):
    sitio = SitioWeb("TiendaLaura.chibchaweb.co", plataforma)
    assert sitio.subdominio == "tiendalaura.chibchaweb.co" and sitio.plataforma is plataforma
    assert not sitio.tiene_dominio_propio() and "tiendalaura" in repr(sitio)


@pytest.mark.parametrize("subdominio", ["", "-malo.chibchaweb.co", "sin_punto", "a" * 64 + ".chibchaweb.co"])
def test_rn14_subdominio_invalido(subdominio):
    with pytest.raises(ValidacionError) as e:
        SitioWeb(subdominio, Plataforma.UNIX)
    assert e.value.campo == "sitio"


def test_rn14_plataforma_debe_ser_enumeracion():
    assert [p.value for p in Plataforma] == ["WINDOWS", "UNIX"]
    with pytest.raises(ValidacionError):
        SitioWeb("a.chibchaweb.co", "UNIX")  # type: ignore[arg-type]


def test_dominio_propio():
    sitio = SitioWeb("a.chibchaweb.co", Plataforma.UNIX, dominio_propio="Tienda.CO")
    assert sitio.tiene_dominio_propio() and sitio.dominio_propio == "tienda.co"
    sitio.asignar_dominio_propio("tienda.co")
    with pytest.raises(ReglaNegocioError):
        sitio.asignar_dominio_propio("otra.com")
    with pytest.raises(ValidacionError):
        SitioWeb("b.chibchaweb.co", Plataforma.UNIX).asignar_dominio_propio("sin punto")


def test_rn03_corte_anclado_al_dia_de_inicio_sin_arrastre(cliente, catalogo):
    mensual = next(p for p in catalogo.listar_planes() if p.meses == 1)
    s = Suscripcion(
        cliente, SitioWeb("b.chibchaweb.co", Plataforma.UNIX), catalogo.buscar_paquete(1), mensual, date(2026, 1, 31)
    )
    cortes = []
    for _ in range(3):
        s.avanzar_corte()
        cortes.append(s.fecha_corte)
    assert cortes == [date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]


def test_cu_cli_03_setters_de_sitio_validan_como_el_constructor():
    sitio = SitioWeb("a.chibchaweb.co", Plataforma.UNIX)
    sitio.subdominio = " Nuevo.ChibchaWeb.co "
    sitio.plataforma = Plataforma.WINDOWS
    assert sitio.subdominio == "nuevo.chibchaweb.co" and sitio.plataforma is Plataforma.WINDOWS
    with pytest.raises(ValidacionError) as e:
        sitio.subdominio = "-malo.chibchaweb.co"
    assert e.value.campo == "sitio" and sitio.subdominio == "nuevo.chibchaweb.co"
    with pytest.raises(ValidacionError) as e:
        sitio.plataforma = "UNIX"  # type: ignore[assignment]
    assert e.value.campo == "plataforma"
