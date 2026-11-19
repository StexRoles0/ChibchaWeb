"""Adaptadores simulados (D-05, D-06): mismas reglas que los reales, sin red."""

from datetime import date
from decimal import Decimal

import pytest

from chibchaweb.adaptadores.simulados import (
    FuenteLegadaSimulada,
    PasarelaPagoSimulada,
    ProveedorAutenticacionSimulado,
    RegistradorDominioSimulado,
    ValidadorMedioPagoSimulado,
)
from chibchaweb.dominio.cuentas import TarjetaCredito
from chibchaweb.dominio.errores import AutorizacionFallidaError, ValidacionError
from chibchaweb.dominio.migracion import (
    CreadorClienteLegado,
    CreadorHostingLegado,
    CreadorPagoLegado,
    NivelLog,
    ProcesoMigracion,
)
from tests import falsos


def tarjeta(numero):
    return TarjetaCredito(numero, date(2030, 1, 1), falsos.franquicias_estandar()[0], "123")


def test_proveedor_dev_devuelve_identidad_verificada():
    identidad = ProveedorAutenticacionSimulado().autorizar("dev:laura.gomez@correo.co")
    assert identidad.identificador_externo == "dev|laura.gomez@correo.co"
    assert (
        identidad.correo == "laura.gomez@correo.co"
        and identidad.correo_verificado
        and identidad.nombre == "Laura Gomez"
    )


def test_proveedor_dev_noverificado_y_codigos_invalidos():
    assert not ProveedorAutenticacionSimulado().autorizar("dev-noverificado:a@b.co").correo_verificado
    for codigo in ("", "dev:", "otro:a@b.co", "sin-prefijo"):
        with pytest.raises(AutorizacionFallidaError):
            ProveedorAutenticacionSimulado().autorizar(codigo)


def test_validador_rechaza_tarjetas_que_terminan_en_0002():
    validador = ValidadorMedioPagoSimulado()
    assert validador.verificar(tarjeta("4242424242424242"))
    assert not validador.verificar(tarjeta("4000000000000002"))


def test_la_tarjeta_rechazada_por_el_validador_falla_con_validacion_error():
    with pytest.raises(ValidacionError) as e:
        tarjeta("4000000000000002").validar(ValidadorMedioPagoSimulado())
    assert e.value.campo == "numeroTarjeta"


def test_pasarela_rechaza_0341_y_devuelve_referencia_uuid8():
    pasarela = PasarelaPagoSimulada()
    assert pasarela.cobrar(tarjeta("4000000000000341"), Decimal("54.00")) == ""
    referencia = pasarela.cobrar(tarjeta("4242424242424242"), Decimal("54.00"))
    assert referencia.startswith("REF-") and len(referencia) == 12 and referencia[4:].isalnum()
    assert referencia != pasarela.cobrar(tarjeta("4242424242424242"), Decimal("54.00"))


def test_registrador_rechaza_dominios_con_rechazo():
    registrador = RegistradorDominioSimulado()
    registrador.enviar("<solicitudDominio><dominio><nombre>tienda</nombre></dominio></solicitudDominio>")
    with pytest.raises(ConnectionError):
        registrador.enviar("<solicitudDominio><dominio><nombre>rechazo-total</nombre></dominio></solicitudDominio>")


# --- fuente legada -------------------------------------------------------------------------------------


@pytest.fixture
def proceso_con_datos_legados():
    catalogo = falsos.RepositorioCatalogoEnMemoria()
    creadores = [
        CreadorClienteLegado(catalogo.franquicias),
        CreadorHostingLegado(catalogo.paquetes, catalogo.planes),
        CreadorPagoLegado(),
    ]
    admin = falsos.roles_estandar()[2]
    from chibchaweb.dominio.cuentas import Empleado

    proceso = ProcesoMigracion(Empleado("Ana", "ana@chibchaweb.co", "300", "E-3", admin, id=3), creadores)
    proceso.simular(FuenteLegadaSimulada())
    return proceso


def test_la_fuente_lee_los_tres_archivos_con_el_tipo_en_cada_linea():
    registros = FuenteLegadaSimulada().leer_registros()
    tipos = [r.partition("|")[0] for r in registros]
    assert tipos.count("CLIENTE") == 11 and tipos.count("HOSTING") == 10 and tipos.count("PAGO") == 11
    assert registros[0].startswith("CLIENTE|L-001,Marta Rojas,")
    assert 'CLIENTE|L-001,Marta Rojas,marta.rojas@ejemplo.co,"Calle 45 # 12-30, Bogotá, 110221"' in registros[0]


def test_los_datos_legados_tienen_filas_validas_e_invalidas(proceso_con_datos_legados):
    p = proceso_con_datos_legados
    assert p.cantidad_validos() > 0 and p.cantidad_invalidos() > 0
    validos = {(e.tipo_registro, e.identificador_legado) for e in p.log if e.nivel is NivelLog.INFO}
    errores = {(e.tipo_registro, e.identificador_legado): e.mensaje for e in p.log if e.es_error()}
    assert {("CLIENTE", f"L-00{n}") for n in range(1, 6)} <= validos
    assert {("HOSTING", f"H-00{n}") for n in range(1, 6)} <= validos
    assert {("PAGO", f"P-00{n}") for n in range(1, 6)} <= validos
    assert "Correo inválido" in errores[("CLIENTE", "L-006")]
    assert "vencida" in errores[("CLIENTE", "L-007")]
    assert "Franquicia AMEX" in errores[("CLIENTE", "L-008")]
    assert "no corresponde a la franquicia" in errores[("CLIENTE", "L-009")]
    assert "Correo repetido" in errores[("CLIENTE", "L-010")]
    assert "Dirección inválida" in errores[("CLIENTE", "L-011")]
    assert "Subdominio inválido" in errores[("HOSTING", "H-006")]
    assert "Chibcha-Diamante" in errores[("HOSTING", "H-007")] and "Quincenal" in errores[("HOSTING", "H-008")]
    assert "L-099" in errores[("HOSTING", "H-009")] and "plataforma" in errores[("HOSTING", "H-010")].lower()
    for n in (6, 7, 8, 9, 10, 11):
        assert ("PAGO", f"P-0{n:02d}") in errores


def test_fuente_con_directorio_sin_archivos(tmp_path):
    from chibchaweb.dominio.errores import ReglaNegocioError

    with pytest.raises(ReglaNegocioError):
        FuenteLegadaSimulada(tmp_path).leer_registros()
