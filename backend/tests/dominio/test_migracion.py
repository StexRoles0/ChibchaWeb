"""Migración legada: RN-25 a RN-28 y el Factory Method de registros."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time

from chibchaweb.dominio.cuentas import Cliente, TarjetaCredito
from chibchaweb.dominio.errores import EstadoInvalidoError, ReglaNegocioError, ValidacionError
from chibchaweb.dominio.facturacion import EstadoPago
from chibchaweb.dominio.hospedaje import Plataforma
from chibchaweb.dominio.migracion import (
    ClienteLegado,
    CreadorClienteLegado,
    CreadorHostingLegado,
    CreadorPagoLegado,
    CreadorRegistroLegado,
    EntradaLog,
    EstadoMigracion,
    HostingLegado,
    NivelLog,
    PagoLegado,
    ProcesoMigracion,
    RegistroLegado,
)
from tests import falsos

CLIENTE_OK = (
    'CLIENTE|L-1,Ana Ruiz,ana@correo.co,"Calle 1 # 2-3, Bogotá, 110111",4242424242424242,3001234567,2030-01-01,VISA'
)
CLIENTE_MAL = "CLIENTE|L-2,Pedro,correo-malo,sin direccion,1234,300,2020-01-01,AMEX"
HOSTING_OK = "HOSTING|H-1,L-1,ana.chibchaweb.co,Chibcha-Oro,Semestral,unix"
HOSTING_MAL = "HOSTING|H-2,L-1,otro.chibchaweb.co,Chibcha-Bronce,Bienal,MAC"
PAGO_OK = "PAGO|P-1,L-1,54.00,2026-06-01,REF-ANTIGUA-1"
PAGO_MAL = "PAGO|P-2,L-1,-5,2099-01-01,"


@pytest.fixture
def creadores():
    return [
        CreadorClienteLegado(falsos.franquicias_estandar()),
        CreadorHostingLegado(falsos.paquetes_estandar(), falsos.planes_estandar()),
        CreadorPagoLegado(),
    ]


@pytest.fixture
def administrador(nuevo_empleado):
    return nuevo_empleado(rol_id=3, correo="admin@chibchaweb.co", id=40)


@pytest.fixture
def proceso(administrador, creadores):
    return ProcesoMigracion(administrador, creadores)


def _fuente(*lineas):
    return falsos.FuenteLegadaFalsa(list(lineas))


# --- Factory Method ----------------------------------------------------------------------------


def test_cada_creador_instancia_su_subtipo(creadores):
    cliente_c, hosting_c, pago_c = creadores
    assert [c.tipo() for c in creadores] == ["CLIENTE", "HOSTING", "PAGO"]
    assert isinstance(cliente_c.crear_registro(CLIENTE_OK.split("|", 1)[1]), ClienteLegado)
    assert isinstance(hosting_c.crear_registro(HOSTING_OK.split("|", 1)[1]), HostingLegado)
    assert isinstance(pago_c.crear_registro(PAGO_OK.split("|", 1)[1]), PagoLegado)
    for clase in (CreadorRegistroLegado, RegistroLegado):
        with pytest.raises(TypeError):
            clase()  # type: ignore[abstract]


def test_procesar_crea_y_valida(creadores):
    registro = creadores[2].procesar(PAGO_OK.split("|", 1)[1])
    assert registro.valido is True and registro.describir_errores() == ""
    invalido = creadores[2].procesar(PAGO_MAL.split("|", 1)[1])
    assert invalido.valido is False and "Monto" in invalido.describir_errores()


@freeze_time("2026-11-16 15:00:00")
def test_cliente_legado_valido_y_conversion(creadores):
    registro = creadores[0].procesar(CLIENTE_OK.split("|", 1)[1])
    assert registro.valido, registro.describir_errores()
    assert (registro.identificador_legado, registro.nombre, registro.correo, registro.telefono) == (
        "L-1",
        "Ana Ruiz",
        "ana@correo.co",
        "3001234567",
    )
    assert registro.numero_tarjeta == "4242424242424242" and registro.franquicia == "VISA"
    assert registro.vencimiento_tarjeta == date(2030, 1, 1) and "Bogotá" in registro.direccion
    cliente = registro.a_cliente()
    assert isinstance(cliente, Cliente) and cliente.cuenta is None  # RN-28
    assert cliente.residencia is not cliente.facturacion and cliente.residencia.ciudad == "Bogotá"
    assert isinstance(cliente.medio_pago, TarjetaCredito) and cliente.medio_pago.codigo_seguridad is None


@freeze_time("2026-11-16 15:00:00")
def test_cliente_legado_invalido_describe_errores(creadores):
    registro = creadores[0].procesar(CLIENTE_MAL.split("|", 1)[1])
    errores = registro.describir_errores()
    assert not registro.valido
    for texto in ("Correo", "Dirección", "AMEX", "vencida"):
        assert texto in errores
    with pytest.raises(ReglaNegocioError):
        registro.a_cliente()


@freeze_time("2026-11-16 15:00:00")
def test_cliente_legado_tarjeta_que_no_cumple_patron(creadores):
    datos = 'L-3,Ana,a@b.co,"Calle 1, Cali, 760001",5555555555554444,1,2030-01-01,VISA'
    registro = creadores[0].procesar(datos)
    assert "no corresponde a la franquicia" in registro.describir_errores()


def test_registro_sin_identificador_ni_campos(creadores):
    registro = creadores[1].procesar("")
    assert not registro.valido and "identificador" in registro.describir_errores()


def test_hosting_legado_valida_contra_catalogo(creadores, cliente, catalogo):
    ok = creadores[1].procesar(HOSTING_OK.split("|", 1)[1])
    assert ok.valido and (ok.identificador_cliente, ok.subdominio, ok.paquete, ok.plan, ok.plataforma) == (
        "L-1",
        "ana.chibchaweb.co",
        "Chibcha-Oro",
        "Semestral",
        "UNIX",
    )
    mal = creadores[1].procesar(HOSTING_MAL.split("|", 1)[1])
    for texto in ("Chibcha-Bronce", "Bienal", "MAC"):
        assert texto in mal.describir_errores()
    oro, semestral = catalogo.buscar_paquete(2), catalogo.buscar_plan(3)
    suscripcion = ok.a_suscripcion(cliente, oro, semestral)
    assert suscripcion.sitio.subdominio == "ana.chibchaweb.co" and suscripcion.sitio.plataforma is Plataforma.UNIX
    assert suscripcion in cliente.suscripciones
    with pytest.raises(ReglaNegocioError):
        ok.a_suscripcion(cliente, catalogo.buscar_paquete(1), semestral)
    with pytest.raises(ReglaNegocioError):
        mal.a_suscripcion(cliente, oro, semestral)


@freeze_time("2026-11-16 15:00:00")
def test_pago_legado_valida_y_se_convierte_en_pago_comisionado(creadores, cliente, nueva_suscripcion):
    ok = creadores[2].procesar(PAGO_OK.split("|", 1)[1])
    assert (ok.identificador_cliente, ok.monto, ok.fecha, ok.referencia) == (
        "L-1",
        Decimal("54.00"),
        date(2026, 6, 1),
        "REF-ANTIGUA-1",
    )
    s = nueva_suscripcion(cliente)
    pago = ok.a_pago(s)
    assert pago.estado is EstadoPago.EXITOSO and pago.comisionado and pago in s.pagos
    mal = creadores[2].procesar(PAGO_MAL.split("|", 1)[1])
    errores = mal.describir_errores()
    assert "Monto" in errores and "futura" in errores and "Referencia" in errores
    with pytest.raises(ReglaNegocioError):
        mal.a_pago(s)
    assert not creadores[2].procesar("P-3,L-1,abc,no-fecha,R").valido


# --- RN-25 estados -----------------------------------------------------------------------------


def test_rn25_flujo_feliz(proceso):
    assert proceso.estado is EstadoMigracion.CREADA and proceso.fecha_fin is None
    proceso.simular(_fuente(CLIENTE_OK))
    assert proceso.estado is EstadoMigracion.SIMULADA
    proceso.aprobar()
    assert proceso.estado is EstadoMigracion.APROBADA and proceso.puede_ejecutarse()
    proceso.marcar_ejecutado()
    assert proceso.estado is EstadoMigracion.EJECUTADA and proceso.fecha_fin is not None


def test_rn25_revertido_desde_aprobada(proceso):
    proceso.simular(_fuente())
    proceso.aprobar()
    proceso.marcar_revertido()
    assert proceso.estado is EstadoMigracion.REVERTIDA and proceso.fecha_fin is not None


@pytest.mark.parametrize("pasos", [[], ["simular"]])
def test_rn25_cancelar_desde_creada_o_simulada(proceso, pasos):
    if pasos:
        proceso.simular(_fuente())
    proceso.cancelar()
    assert proceso.estado is EstadoMigracion.CANCELADA


@pytest.mark.parametrize(
    ("previos", "accion"),
    [
        ([], "aprobar"),
        ([], "marcar_ejecutado"),
        ([], "marcar_revertido"),
        (["simular"], "marcar_ejecutado"),
        (["simular", "aprobar"], "cancelar"),
        (["simular", "aprobar"], "aprobar"),
        (["simular", "aprobar", "marcar_ejecutado"], "marcar_revertido"),
        (["simular", "aprobar", "marcar_ejecutado"], "cancelar"),
        (["cancelar"], "aprobar"),
        (["simular"], "simular"),
    ],
)
def test_rn25_transiciones_invalidas(proceso, previos, accion):
    for paso in previos:
        getattr(proceso, paso)(_fuente()) if paso == "simular" else getattr(proceso, paso)()
    with pytest.raises(EstadoInvalidoError):
        getattr(proceso, accion)(_fuente()) if accion == "simular" else getattr(proceso, accion)()


def test_rn25_proceso_validaciones(administrador, creadores):
    with pytest.raises(ValidacionError):
        ProcesoMigracion(administrador, [])
    with pytest.raises(ValidacionError):
        ProcesoMigracion(None, creadores)  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        ProcesoMigracion(administrador, [CreadorPagoLegado(), CreadorPagoLegado()])
    with pytest.raises(ValidacionError):
        ProcesoMigracion(administrador, creadores, estado="CREADA")  # type: ignore[arg-type]
    p = ProcesoMigracion(administrador, creadores)
    assert p.ejecutor is administrador and len(p.creadores) == 3 and p.fecha_inicio and "CREADA" in repr(p)
    assert [e.value for e in EstadoMigracion] == [
        "CREADA",
        "SIMULADA",
        "APROBADA",
        "EJECUTADA",
        "REVERTIDA",
        "CANCELADA",
    ]


# --- RN-26 simulación -------------------------------------------------------------------------


@freeze_time("2026-11-16 15:00:00")
def test_rn26_simulacion_llena_el_log_sin_escribir_datos(proceso):
    proceso.simular(_fuente(CLIENTE_OK, CLIENTE_MAL, HOSTING_OK, HOSTING_MAL, PAGO_OK, PAGO_MAL))
    assert proceso.cantidad_validos() == 3 and proceso.cantidad_invalidos() == 3
    assert len(proceso.registros) == 6
    niveles = [(e.nivel, e.tipo_registro, e.identificador_legado) for e in proceso.log]
    assert niveles == [
        (NivelLog.INFO, "CLIENTE", "L-1"),
        (NivelLog.ERROR, "CLIENTE", "L-2"),
        (NivelLog.INFO, "HOSTING", "H-1"),
        (NivelLog.ERROR, "HOSTING", "H-2"),
        (NivelLog.INFO, "PAGO", "P-1"),
        (NivelLog.ERROR, "PAGO", "P-2"),
    ]
    assert "Correo inválido" in proceso.log[1].mensaje and proceso.log[1].es_error()


@freeze_time("2026-11-16 15:00:00")
def test_rn26_referencias_entre_registros(proceso):
    proceso.simular(
        _fuente(
            CLIENTE_OK,
            CLIENTE_OK.replace("ana@", "ana2@"),  # identificador repetido
            CLIENTE_OK.replace("L-1", "L-9"),  # correo repetido
            "HOSTING|H-9,L-404,x.chibchaweb.co,Chibcha-Oro,Mensual,UNIX",  # cliente inexistente
            HOSTING_OK,
            HOSTING_OK.replace("H-1", "H-3"),  # subdominio repetido
            "PAGO|P-9,L-404,10,2026-01-01,R",  # cliente inexistente
        )
    )
    mensajes = [e.mensaje for e in proceso.log if e.es_error()]
    assert any("repetido" in m and "Identificador" in m for m in mensajes)
    assert any("Correo repetido" in m for m in mensajes)
    assert any("Subdominio repetido" in m for m in mensajes)
    assert sum("L-404" in m for m in mensajes) == 2
    assert proceso.cantidad_validos() == 2


@freeze_time("2026-11-16 15:00:00")
def test_rn26_pago_de_cliente_sin_hospedaje_es_invalido(proceso):
    proceso.simular(_fuente(CLIENTE_OK, PAGO_OK))
    assert proceso.log[-1].es_error() and "hospedaje" in proceso.log[-1].mensaje


def test_rn26_lineas_sin_tipo_reconocido_van_al_log(proceso):
    proceso.simular(_fuente("BASURA", "OTRO|x,y"))
    assert proceso.cantidad_validos() == 0 and proceso.registros == ()
    assert all(e.es_error() and e.tipo_registro is None for e in proceso.log)
    assert len(proceso.log) == 2


def test_entrada_log(proceso):
    e = EntradaLog(NivelLog.ADVERTENCIA, "dato incompleto", identificador_legado="L-1", tipo_registro="CLIENTE")
    proceso.agregar_entrada(e)
    assert proceso.log == (e,) and not e.es_error() and e.fecha and e.mensaje == "dato incompleto"
    assert "CLIENTE" in repr(e)
    with pytest.raises(ValidacionError):
        EntradaLog(NivelLog.INFO, "")
    with pytest.raises(ValidacionError):
        EntradaLog("INFO", "x")  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        EntradaLog(NivelLog.INFO, "x", tipo_registro="OTRO")
    assert [n.value for n in NivelLog] == ["INFO", "ADVERTENCIA", "ERROR"]


# --- RN-27 confirmación ------------------------------------------------------------------------


@freeze_time("2026-11-16 15:00:00")
def test_rn27_preparar_ejecucion_relee_sin_escribir_log(proceso):
    fuente = _fuente(CLIENTE_OK, CLIENTE_MAL, HOSTING_OK, PAGO_OK)
    proceso.simular(fuente)
    entradas = len(proceso.log)
    proceso.aprobar()
    proceso.preparar_ejecucion(fuente)
    assert len(proceso.log) == entradas and proceso.cantidad_validos() == 3


@freeze_time("2026-11-16 15:00:00")
def test_rn27_fuente_cambiada_desde_la_simulacion(proceso):
    fuente = _fuente(CLIENTE_OK, HOSTING_OK)
    proceso.simular(fuente)
    proceso.aprobar()
    fuente.registros.append(PAGO_OK)
    with pytest.raises(ReglaNegocioError, match="La fuente cambió desde la simulación"):
        proceso.preparar_ejecucion(fuente)


def test_rn27_preparar_exige_aprobado(proceso):
    with pytest.raises(EstadoInvalidoError):
        proceso.preparar_ejecucion(_fuente())


@freeze_time("2026-11-16 15:00:00")
def test_rn27_proceso_reconstruido_usa_el_log_persistido(administrador, creadores, proceso):
    fuente = _fuente(CLIENTE_OK, HOSTING_OK)
    proceso.simular(fuente)
    recargado = ProcesoMigracion(administrador, creadores, id=1, estado=EstadoMigracion.SIMULADA, log=list(proceso.log))
    recargado.aprobar()
    recargado.preparar_ejecucion(fuente)
    assert recargado.cantidad_validos() == 2


# --- RN-28 clientes migrados -------------------------------------------------------------------


@freeze_time("2026-11-16 15:00:00")
def test_rn28_migrado_sin_cuenta_y_tarjeta_sin_validador_externo(creadores):
    validador = falsos.ValidadorMedioPagoFalso()
    datos = 'L-5,Eva,eva@x.co,"Calle 1, Cali, 760001",4000000000000002,1,2030-01-01,VISA'
    registro = creadores[0].procesar(datos)  # termina en 0002: el validador externo la rechazaría
    assert registro.valido
    cliente = registro.a_cliente()
    assert cliente.cuenta is None and validador.verificados == []
