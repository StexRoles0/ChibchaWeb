"""CU-MIG-01: ``/migraciones`` (api.md §Migración) con PostgreSQL y la fuente legada simulada (D-06)."""

from datetime import date

from django.utils import timezone

from chibchaweb.dominio.migracion import EstadoMigracion
from config.contenedor import contenedor
from tests.web.conftest import BASE, assert_error, cliente_en_sesion

RUTA = f"{BASE}/migraciones"


def simular(admin):
    r = admin.post(RUTA, {}, format="json")
    assert r.status_code == 201, r.content
    return r.json()


def confirmar(http, id):
    return http.post(f"{RUTA}/{id}/confirmacion", {}, format="json")


def cancelar(http, id):
    return http.post(f"{RUTA}/{id}/cancelacion", {}, format="json")


def correos_migrados(gestion):
    filas = gestion.get(f"{BASE}/consultas/CLIENTE", {"filtro": "@ejemplo.co"}).json()
    return sorted(f["subtitulo"].split(" · ")[0] for f in filas)


# --- fase 1 ------------------------------------------------------------------------------------
def test_simular_201_con_el_resultado_y_el_log_de_la_fuente_simulada(admin):
    r = simular(admin)
    assert set(r) == {"idProceso", "validos", "invalidos", "entradas"}
    assert r["validos"] > 0 and r["invalidos"] > 0  # los CSV de ejemplo traen filas válidas e inválidas
    assert len(r["entradas"]) == r["validos"] + r["invalidos"]
    for entrada in r["entradas"]:
        nivel, tipo, _id_legado, mensaje = entrada.split("|", 3)
        assert nivel in ("INFO", "ADVERTENCIA", "ERROR") and tipo in ("CLIENTE", "HOSTING", "PAGO") and mensaje
    assert sum(e.startswith("ERROR|") for e in r["entradas"]) == r["invalidos"]
    assert contenedor().migraciones.buscar_por_id(r["idProceso"]).estado is EstadoMigracion.SIMULADA


def test_simular_no_escribe_datos_de_negocio(admin, gestion):
    simular(admin)
    assert correos_migrados(gestion) == []


# --- fase 2 ------------------------------------------------------------------------------------
def test_confirmar_ejecuta_y_deja_los_clientes_sin_cuenta_con_corte_hoy(admin, gestion):
    r = simular(admin)
    respuesta = confirmar(admin, r["idProceso"])
    assert respuesta.status_code == 200 and respuesta.json() == {"estado": "EJECUTADA"}
    migrados = correos_migrados(gestion)
    assert "marta.rojas@ejemplo.co" in migrados and len(migrados) == len(set(migrados))
    c = contenedor()
    marta = c.usuarios.buscar_por_correo("marta.rojas@ejemplo.co")
    assert marta.cuenta is None  # RN-28: la vincula en su primer ingreso
    (s,) = marta.suscripciones
    assert s.fecha_inicio == s.fecha_corte == timezone.localdate()  # D-31
    assert len(s.pagos) == 2 and all(p.comisionado and p.es_exitoso() for p in s.pagos)
    proceso = c.migraciones.buscar_por_id(r["idProceso"])
    assert proceso.estado is EstadoMigracion.EJECUTADA and proceso.log[-1].mensaje.startswith("Migración ejecutada")


def test_un_cliente_migrado_entra_por_correo_verificado_rn07(admin):
    from tests.web.conftest import entrar

    confirmar(admin, simular(admin)["idProceso"])
    from rest_framework.test import APIClient

    marta = APIClient()
    r = entrar(marta, "marta.rojas@ejemplo.co")
    assert r.status_code == 200 and r.json()["registrado"] is True and r.json()["tipoUsuario"] == "CLIENTE"


def test_el_cobro_programado_cobra_a_los_migrados_desde_el_dia_siguiente(admin):
    """D-31: nacen con corte = hoy, así que ``cargar_pagos`` de mañana las encuentra vencidas."""
    confirmar(admin, simular(admin)["idProceso"])
    vencidas = contenedor().suscripciones.buscar_vencidas(date.fromordinal(timezone.localdate().toordinal() + 1))
    assert any(s.titular.correo == "marta.rojas@ejemplo.co" for s in vencidas)


def test_rn27_si_falla_una_escritura_se_revierte_todo_y_queda_revertida(admin, gestion):
    """Carlos ya existe: Marta (L-001) se alcanza a escribir y se deshace; el proceso queda REVERTIDA."""
    cliente_en_sesion("carlos.pardo@ejemplo.co")  # mismo correo que L-002 del legado
    r = simular(admin)
    respuesta = confirmar(admin, r["idProceso"])
    assert respuesta.status_code == 200 and respuesta.json() == {"estado": "REVERTIDA"}
    assert correos_migrados(gestion) == ["carlos.pardo@ejemplo.co"]  # solo el que ya existía
    assert contenedor().usuarios.buscar_por_correo("marta.rojas@ejemplo.co") is None
    proceso = contenedor().migraciones.buscar_por_id(r["idProceso"])
    assert proceso.estado is EstadoMigracion.REVERTIDA and proceso.fecha_fin is not None
    assert proceso.log[-1].nivel.value == "ERROR" and "correo" in proceso.log[-1].mensaje.lower()
    assert_error(confirmar(admin, r["idProceso"]), 409, "ESTADO_INVALIDO")


def test_rn27_si_la_fuente_cambio_desde_la_simulacion_es_422_y_no_escribe(admin, gestion, monkeypatch):
    r = simular(admin)
    monkeypatch.setattr(contenedor().fuente_legada, "leer_registros", lambda: [])
    assert_error(confirmar(admin, r["idProceso"]), 422, "REGLA_NEGOCIO")
    assert correos_migrados(gestion) == []
    assert contenedor().migraciones.buscar_por_id(r["idProceso"]).estado is EstadoMigracion.SIMULADA


# --- transiciones RN-25 ------------------------------------------------------------------------
def test_rn25_confirmar_dos_veces_es_409(admin):
    id = simular(admin)["idProceso"]
    assert confirmar(admin, id).status_code == 200
    assert_error(confirmar(admin, id), 409, "ESTADO_INVALIDO")


def test_rn25_cancelar_una_simulada_200_y_ya_no_se_puede_confirmar(admin, gestion):
    id = simular(admin)["idProceso"]
    r = cancelar(admin, id)
    assert r.status_code == 200 and r.json() == {"estado": "CANCELADA"}
    assert_error(confirmar(admin, id), 409, "ESTADO_INVALIDO")
    assert_error(cancelar(admin, id), 409, "ESTADO_INVALIDO")
    assert correos_migrados(gestion) == []


def test_rn25_cancelar_una_ejecutada_es_409(admin):
    id = simular(admin)["idProceso"]
    confirmar(admin, id)
    assert_error(cancelar(admin, id), 409, "ESTADO_INVALIDO")


def test_proceso_inexistente_es_404(admin):
    assert_error(confirmar(admin, 999999), 404, "NO_ENCONTRADO")
    assert_error(cancelar(admin, 999999), 404, "NO_ENCONTRADO")


# --- permisos ----------------------------------------------------------------------------------
def test_solo_el_administrador_con_migrar_datos(anonimo, gestion, soporte, cliente_http, admin):
    id = simular(admin)["idProceso"]
    for http in (gestion, soporte, cliente_http):
        assert_error(http.post(RUTA, {}, format="json"), 403, "SIN_PERMISO")
        assert_error(confirmar(http, id), 403, "SIN_PERMISO")
        assert_error(cancelar(http, id), 403, "SIN_PERMISO")
    assert_error(anonimo.post(RUTA, {}, format="json"), 401, "NO_AUTENTICADO")
    assert_error(confirmar(anonimo, id), 401, "NO_AUTENTICADO")
