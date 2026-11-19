"""CU-MIG-01: simular, confirmar y cancelar (RN-25, RN-26, RN-27, RN-28) con repositorios en memoria."""

from datetime import date

import pytest
from freezegun import freeze_time

from chibchaweb.dominio.errores import (
    ContingenciaActivaError,
    ErrorDominio,
    EstadoInvalidoError,
    NoEncontradoError,
    ReglaNegocioError,
    UsuarioInactivoError,
)
from chibchaweb.dominio.migracion import EstadoMigracion, NivelLog
from chibchaweb.servicio.dto import ResultadoMigracionDTO

CLIENTE_1 = (
    'CLIENTE|L-001,Marta Rojas,marta@ejemplo.co,"Calle 45 # 12-30, Bogotá, 110221",4111111111111111,3101112233,'
    "2029-08-01,VISA"
)
CLIENTE_2 = (
    'CLIENTE|L-002,Carlos Pardo,carlos@ejemplo.co,"Carrera 15 # 80-11, Bogotá, 110111",5555555555554444,3112223344,'
    "2028-05-01,MASTERCARD"
)
CLIENTE_MALO = 'CLIENTE|L-003,Sin Dirección,sin@ejemplo.co,"",4111111111111111,3101112233,2029-08-01,VISA'
CLIENTE_VENCIDO = (
    'CLIENTE|L-004,Diana,diana@ejemplo.co,"Calle 1, Cali, 760001",4012888888881881,3101112233,2020-01-01,VISA'
)
HOSTING_1 = "HOSTING|H-001,L-001,floristeria.chibchaweb.com,Chibcha-Oro,Semestral,UNIX"
HOSTING_2 = "HOSTING|H-002,L-002,pardo.chibchaweb.com,Chibcha-Plata,Mensual,WINDOWS"
HOSTING_PLAN_MALO = "HOSTING|H-003,L-001,otro.chibchaweb.com,Chibcha-Oro,Quincenal,UNIX"
PAGO_1 = "PAGO|P-001,L-001,54.00,2026-05-02,LEG-0001"
PAGO_2 = "PAGO|P-002,L-002,5.00,2026-10-15,LEG-0003"
PAGO_MALO = "PAGO|P-003,L-001,-5,2026-10-15,LEG-0009"
FUENTE = [CLIENTE_1, CLIENTE_2, HOSTING_1, HOSTING_2, PAGO_1, PAGO_2]

pytestmark = pytest.mark.usefixtures("hoy_fijo")


@pytest.fixture
def hoy_fijo():
    with freeze_time("2026-12-01 10:00:00-05:00"):
        yield


@pytest.fixture
def ejecutor(empleado_gestion):
    return empleado_gestion


@pytest.fixture
def simulada(migracion, fuente, ejecutor):
    fuente.registros = list(FUENTE)
    return migracion.migrar_registros_legados(ejecutor.id)


# --- fase 1: simulación (RN-26) ----------------------------------------------------------------
def test_rn26_simulacion_cuenta_validos_e_invalidos_y_arma_el_log(migracion, fuente, ejecutor, migraciones, usuarios):
    fuente.registros = [CLIENTE_1, CLIENTE_MALO, CLIENTE_VENCIDO, HOSTING_1, HOSTING_PLAN_MALO, PAGO_1, PAGO_MALO]
    r = migracion.migrar_registros_legados(ejecutor.id)
    assert isinstance(r, ResultadoMigracionDTO)
    assert (r.validos, r.invalidos) == (3, 4) and len(r.entradas) == 7
    niveles = [e.split("|")[0] for e in r.entradas]
    assert niveles.count("INFO") == 3 and niveles.count("ERROR") == 4
    assert r.entradas[0] == "INFO|CLIENTE|L-001|Registro válido"
    error = next(e for e in r.entradas if "|L-003|" in e)
    assert error.startswith("ERROR|CLIENTE|L-003|") and "Dirección inválida" in error
    assert any("Tarjeta vencida" in e for e in r.entradas)
    assert any("|H-003|" in e and "plan" in e.lower() for e in r.entradas)
    proceso = migraciones.buscar_por_id(r.id_proceso)
    assert proceso.estado is EstadoMigracion.SIMULADA and len(proceso.log) == 7
    assert all(not isinstance(u, type(None)) for u in usuarios.objetos.values())
    assert len(usuarios.objetos) == 1  # RN-26: solo está el ejecutor; no se escribió ningún dato de negocio


def test_rn26_las_entradas_con_tipo_desconocido_son_errores_sin_tipo(migracion, fuente, ejecutor):
    fuente.registros = ["OTRO|x,y", CLIENTE_1]
    r = migracion.migrar_registros_legados(ejecutor.id)
    assert any(e.startswith("ERROR|||") and "sin tipo reconocido" in e for e in r.entradas)


def test_fuente_vacia_simula_sin_registros(migracion, fuente, ejecutor):
    r = migracion.migrar_registros_legados(ejecutor.id)
    assert (r.validos, r.invalidos, r.entradas) == (0, 0, ())


def test_solo_un_empleado_activo_puede_simular(migracion, cliente_suelto, ejecutor, usuarios):
    with pytest.raises(ReglaNegocioError):
        migracion.migrar_registros_legados(cliente_suelto.id)
    ejecutor.inactivar()
    with pytest.raises(UsuarioInactivoError):
        migracion.migrar_registros_legados(ejecutor.id)
    with pytest.raises(NoEncontradoError):
        migracion.migrar_registros_legados(9999)


# --- fase 2: confirmación (RN-27, RN-28) -------------------------------------------------------
def test_rn27_confirmar_escribe_clientes_suscripciones_y_pagos_en_una_transaccion(
    migracion, simulada, migraciones, usuarios, suscripciones, unidad
):
    assert migracion.confirmar_migracion(simulada.id_proceso) is EstadoMigracion.EJECUTADA
    assert unidad.llamadas == ["iniciar", "confirmar"]
    clientes = [u for u in usuarios.objetos.values() if u.correo.endswith("@ejemplo.co")]
    assert {c.correo for c in clientes} == {"marta@ejemplo.co", "carlos@ejemplo.co"}
    assert len(suscripciones.objetos) == 2 and len(suscripciones.pagos) == 2
    proceso = migraciones.buscar_por_id(simulada.id_proceso)
    assert proceso.estado is EstadoMigracion.EJECUTADA and proceso.fecha_fin is not None
    assert proceso.log[-1].nivel is NivelLog.INFO and "2 clientes, 2 suscripciones y 2 pagos" in proceso.log[-1].mensaje


def test_rn28_los_clientes_migrados_no_tienen_cuenta_y_su_tarjeta_no_pasa_por_el_validador(
    migracion, simulada, usuarios, validador
):
    migracion.confirmar_migracion(simulada.id_proceso)
    marta = usuarios.buscar_por_correo("marta@ejemplo.co")
    assert marta.cuenta is None and marta.medio_pago.numero == "4111111111111111"
    assert marta.medio_pago.codigo_seguridad is None
    assert validador.verificados == []


def test_las_suscripciones_migradas_nacen_con_corte_hoy_y_los_pagos_historicos_ya_estan_comisionados(
    migracion, simulada, suscripciones
):
    """D-31: corte = hoy (RN-04); los pagos del legado no generan comisiones."""
    migracion.confirmar_migracion(simulada.id_proceso)
    for s in suscripciones.objetos.values():
        assert s.fecha_inicio == s.fecha_corte == date(2026, 12, 1)
    assert all(p.comisionado and p.es_exitoso() for p in suscripciones.pagos.values())
    assert {str(p.monto) for p in suscripciones.pagos.values()} == {"54.00", "5.00"}


def test_rn27_solo_se_escriben_los_registros_validos(migracion, fuente, ejecutor, usuarios, suscripciones):
    fuente.registros = [CLIENTE_1, CLIENTE_MALO, HOSTING_1, HOSTING_PLAN_MALO, PAGO_1, PAGO_MALO]
    id = migracion.migrar_registros_legados(ejecutor.id).id_proceso
    assert migracion.confirmar_migracion(id) is EstadoMigracion.EJECUTADA
    assert usuarios.buscar_por_correo("sin@ejemplo.co") is None
    assert len(suscripciones.objetos) == 1 and len(suscripciones.pagos) == 1


def test_rn27_si_la_fuente_cambio_desde_la_simulacion_no_se_escribe_nada(
    migracion, simulada, fuente, migraciones, usuarios, unidad
):
    fuente.registros = [CLIENTE_1]  # ya no es lo mismo
    with pytest.raises(ReglaNegocioError, match="La fuente cambió"):
        migracion.confirmar_migracion(simulada.id_proceso)
    assert unidad.llamadas == [] and len(usuarios.objetos) == 1
    assert migraciones.buscar_por_id(simulada.id_proceso).estado is EstadoMigracion.SIMULADA


def test_rn27_si_falla_una_escritura_se_revierte_todo_y_queda_revertida(
    migracion, simulada, migraciones, usuarios, suscripciones, unidad, monkeypatch
):
    def falla(pago):
        raise ErrorDominio("falla simulada al escribir el pago")

    monkeypatch.setattr(suscripciones, "registrar_pago", falla)
    assert migracion.confirmar_migracion(simulada.id_proceso) is EstadoMigracion.REVERTIDA
    assert unidad.llamadas == ["iniciar", "revertir"]  # nunca se confirmó
    proceso = migraciones.buscar_por_id(simulada.id_proceso)
    assert proceso.estado is EstadoMigracion.REVERTIDA and proceso.fecha_fin is not None
    assert proceso.log[-1].nivel is NivelLog.ERROR and "falla simulada al escribir el pago" in proceso.log[-1].mensaje


def test_rn27_el_estado_revertida_se_guarda_despues_de_revertir(
    migracion, simulada, migraciones, usuarios, unidad, monkeypatch
):
    orden = []
    monkeypatch.setattr(usuarios, "insertar", lambda c: (_ for _ in ()).throw(ErrorDominio("duplicado")))
    original = migraciones.actualizar
    monkeypatch.setattr(unidad, "revertir", lambda: (orden.append("revertir"), unidad.llamadas.append("revertir")))
    monkeypatch.setattr(migraciones, "actualizar", lambda p: (orden.append(p.estado.value), original(p)))
    migracion.confirmar_migracion(simulada.id_proceso)
    assert orden == ["revertir", "REVERTIDA"]


def test_un_error_que_no_es_del_dominio_tambien_revierte_sin_filtrar_su_mensaje(
    migracion, simulada, migraciones, usuarios, monkeypatch
):
    monkeypatch.setattr(usuarios, "insertar", lambda c: (_ for _ in ()).throw(RuntimeError("secreto 4111")))
    assert migracion.confirmar_migracion(simulada.id_proceso) is EstadoMigracion.REVERTIDA
    mensaje = migraciones.buscar_por_id(simulada.id_proceso).log[-1].mensaje
    assert "RuntimeError" in mensaje and "4111" not in mensaje


def test_si_la_bd_cae_a_mitad_de_la_ejecucion_se_revierte_y_se_avisa_sin_marcar_revertida(
    migracion, simulada, migraciones, usuarios, unidad
):
    usuarios.fallar_con = ContingenciaActivaError("BD caída; evento respaldado.")
    with pytest.raises(ContingenciaActivaError):
        migracion.confirmar_migracion(simulada.id_proceso)
    assert unidad.llamadas == ["iniciar", "revertir"]
    assert migraciones.buscar_por_id(simulada.id_proceso).estado is EstadoMigracion.SIMULADA


def test_si_revertir_falla_el_error_original_no_se_pierde(
    migracion, simulada, migraciones, usuarios, unidad, monkeypatch
):
    def rota():
        raise RuntimeError("conexión rota")

    monkeypatch.setattr(unidad, "revertir", rota)
    monkeypatch.setattr(usuarios, "insertar", lambda c: (_ for _ in ()).throw(ErrorDominio("duplicado")))
    assert migracion.confirmar_migracion(simulada.id_proceso) is EstadoMigracion.REVERTIDA


# --- transiciones RN-25 ------------------------------------------------------------------------
def test_rn25_confirmar_dos_veces_es_estado_invalido(migracion, simulada):
    migracion.confirmar_migracion(simulada.id_proceso)
    with pytest.raises(EstadoInvalidoError):
        migracion.confirmar_migracion(simulada.id_proceso)


def test_rn25_confirmar_una_revertida_es_estado_invalido(migracion, simulada, suscripciones, monkeypatch):
    monkeypatch.setattr(suscripciones, "registrar_pago", lambda p: (_ for _ in ()).throw(ErrorDominio("x")))
    assert migracion.confirmar_migracion(simulada.id_proceso) is EstadoMigracion.REVERTIDA
    with pytest.raises(EstadoInvalidoError):
        migracion.confirmar_migracion(simulada.id_proceso)


def test_rn25_cancelar_una_simulada(migracion, simulada, migraciones, unidad):
    assert migracion.cancelar_migracion(simulada.id_proceso) is None
    proceso = migraciones.buscar_por_id(simulada.id_proceso)
    assert proceso.estado is EstadoMigracion.CANCELADA and proceso.fecha_fin is not None
    with pytest.raises(EstadoInvalidoError):
        migracion.confirmar_migracion(simulada.id_proceso)
    assert unidad.llamadas == []


def test_rn25_cancelar_una_ejecutada_o_dos_veces_es_estado_invalido(migracion, simulada):
    migracion.confirmar_migracion(simulada.id_proceso)
    with pytest.raises(EstadoInvalidoError):
        migracion.cancelar_migracion(simulada.id_proceso)


def test_rn25_cancelar_dos_veces_es_estado_invalido(migracion, simulada):
    migracion.cancelar_migracion(simulada.id_proceso)
    with pytest.raises(EstadoInvalidoError):
        migracion.cancelar_migracion(simulada.id_proceso)


def test_proceso_inexistente_es_404(migracion):
    for operacion in (migracion.confirmar_migracion, migracion.cancelar_migracion):
        with pytest.raises(NoEncontradoError):
            operacion(999)
