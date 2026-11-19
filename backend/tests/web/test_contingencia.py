"""RT04: ``/contingencia/*`` (api.md §Contingencia) con PostgreSQL y el archivo de respaldo real (en tmp_path)."""

import json
from contextlib import contextmanager
from unittest import mock

import pytest
from django.db import OperationalError

from config.contenedor import contenedor
from tests.web.conftest import BASE, assert_error

PENDIENTES = f"{BASE}/contingencia/pendientes"
ALGORITMO = f"{BASE}/contingencia/algoritmo"
SINCRONIZACION = f"{BASE}/contingencia/sincronizacion"
ME = f"{BASE}/clientes/me"


@contextmanager
def bd_sin_escrituras():
    """Las lecturas funcionan y toda escritura del ORM falla: así llega la caída a ``con_contingencia``."""
    from django.db.models import Model
    from django.db.models.query import QuerySet

    with (
        mock.patch.object(Model, "save", side_effect=OperationalError("sin BD")),
        mock.patch.object(QuerySet, "update", side_effect=OperationalError("sin BD")),
    ):
        yield


def renombrar(http, nombre):
    return http.patch(f"{ME}?categoria=PERSONAL", {"nombre": nombre}, format="json")


def nombre_de(http) -> str:
    campos = dict(c.split(": ", 1) for c in http.get(ME).json()["campos"])
    return campos["nombre"]


@pytest.fixture
def evento_pendiente(cliente_http):
    """Un ``Usuario.actualizar`` respaldado porque la BD cayó al renombrar al cliente."""
    with bd_sin_escrituras():
        assert_error(renombrar(cliente_http, "Laura Nueva"), 503, "CONTINGENCIA")
    return cliente_http


# --- GET /contingencia/pendientes (P-06) ------------------------------------------------------
def test_sin_eventos_la_lista_esta_vacia(admin):
    r = admin.get(PENDIENTES)
    assert r.status_code == 200 and r.json() == []


def test_lista_tipo_de_evento_y_algoritmo_sin_el_contenido(admin, evento_pendiente):
    r = admin.get(PENDIENTES)
    assert r.status_code == 200
    assert r.json() == [{"id": 1, "titulo": "Usuario.actualizar", "subtitulo": "AES", "estado": "PENDIENTE"}]
    assert "4242" not in r.content.decode() and "Laura" not in r.content.decode()


# --- PUT /contingencia/algoritmo (RN-29) ------------------------------------------------------
@pytest.mark.parametrize("nombre", ["AES", "ChaCha20", "Camellia", "Twofish"])
def test_cambiar_el_algoritmo_204_y_los_respaldos_nuevos_lo_usan(admin, cliente_http, nombre):
    assert admin.put(ALGORITMO, {"nombre": nombre}, format="json").status_code == 204
    assert contenedor().gestor.algoritmo_activo == nombre
    with bd_sin_escrituras():
        assert_error(renombrar(cliente_http, "Otra"), 503, "CONTINGENCIA")
    assert admin.get(PENDIENTES).json()[0]["subtitulo"] == nombre


def test_algoritmo_desconocido_es_422_validacion_en_nombre(admin):
    assert_error(admin.put(ALGORITMO, {"nombre": "DES"}, format="json"), 422, "VALIDACION", "nombre")
    assert contenedor().gestor.algoritmo_activo == "AES"


def test_algoritmo_sin_nombre_es_400(admin):
    assert_error(admin.put(ALGORITMO, {}, format="json"), 400, "SOLICITUD_INVALIDA", "nombre")


def test_rn29_los_eventos_de_un_algoritmo_anterior_se_sincronizan(admin, cliente_http):
    with bd_sin_escrituras():
        assert_error(renombrar(cliente_http, "Con AES"), 503, "CONTINGENCIA")
    admin.put(ALGORITMO, {"nombre": "Twofish"}, format="json")
    with bd_sin_escrituras():
        assert_error(renombrar(cliente_http, "Con Twofish"), 503, "CONTINGENCIA")
    assert [p["subtitulo"] for p in admin.get(PENDIENTES).json()] == ["AES", "Twofish"]
    assert admin.post(SINCRONIZACION, {}, format="json").json() == {"sincronizados": 2}
    assert nombre_de(cliente_http) == "Con Twofish"  # en el orden en que se escribieron


# --- POST /contingencia/sincronizacion (RN-30, D-27) ------------------------------------------
def test_sincronizar_sin_eventos_devuelve_cero(admin):
    r = admin.post(SINCRONIZACION, {}, format="json")
    assert r.status_code == 200 and r.json() == {"sincronizados": 0}


def test_sincronizar_reinserta_los_eventos_y_vacia_el_respaldo(admin, evento_pendiente):
    assert nombre_de(evento_pendiente) != "Laura Nueva"  # la escritura no llegó a la BD
    r = admin.post(SINCRONIZACION, {}, format="json")
    assert r.status_code == 200 and r.json() == {"sincronizados": 1}
    assert nombre_de(evento_pendiente) == "Laura Nueva"
    assert admin.get(PENDIENTES).json() == []
    assert contenedor().gestor.medio.leer_pendientes() == []


def test_rn30_si_un_evento_falla_todo_se_revierte_y_el_respaldo_se_conserva(admin, evento_pendiente):
    """El 2.º evento apunta a un usuario que no existe: el 1.º (ya aplicado) se deshace y nada se vacía."""
    gestor = contenedor().gestor
    tipo, _, contenido = gestor.recuperar_pendientes()[0].partition("|")
    roto = json.loads(contenido) | {"id": 999999}
    gestor.respaldar(tipo, json.dumps(roto))

    r = admin.post(SINCRONIZACION, {}, format="json")
    assert_error(r, 422, "REGLA_NEGOCIO")
    assert "evento 2 de 2" in r.json()["mensaje"] and "1 de 2" in r.json()["mensaje"]
    assert nombre_de(evento_pendiente) != "Laura Nueva"  # el primer evento se revirtió
    assert len(admin.get(PENDIENTES).json()) == 2  # el medio no se vació
    assert_error(admin.post(SINCRONIZACION, {}, format="json"), 422, "REGLA_NEGOCIO")  # reintentar no duplica


def _con_evento_extra(gestor, tipo, contenido):
    gestor.respaldar(tipo, json.dumps(contenido))


def test_d27_evento_usuario_actualizar_malformado_es_422_y_no_reinserta_nada(admin, evento_pendiente):
    _con_evento_extra(contenedor().gestor, "Usuario.actualizar", {"_operacion": "actualizar", "id": 9999})
    r = admin.post(SINCRONIZACION, {}, format="json")
    assert_error(r, 422, "REGLA_NEGOCIO")
    assert "evento 2 de 2" in r.json()["mensaje"] and "Se procesaron 1 de 2" in r.json()["mensaje"]
    assert nombre_de(evento_pendiente) != "Laura Nueva"  # el 1.º se revirtió
    assert len(admin.get(PENDIENTES).json()) == 2  # medio intacto


def test_d27_solicitud_que_rompe_un_check_es_422_y_tras_corregir_el_respaldo_se_sincroniza(admin, evento_pendiente):
    gestor = contenedor().gestor
    corregido_usuario = json.loads(gestor.recuperar_pendientes()[0].partition("|")[2])
    id_cliente = corregido_usuario["id"]
    malo = {
        "_operacion": "insertar", "id": None, "id_solicitante": id_cliente, "nombre": "x", "extension": "co",
        "estado": "ENVIADA", "fecha_solicitud": "2026-01-01T00:00:00-05:00", "fecha_envio": None,
    }  # fmt: skip
    _con_evento_extra(gestor, "SolicitudDominio.insertar", malo)
    assert_error(admin.post(SINCRONIZACION, {}, format="json"), 422, "REGLA_NEGOCIO")
    assert len(admin.get(PENDIENTES).json()) == 2
    assert contenedor().solicitudes.buscar_por_solicitante(id_cliente) == []
    # el administrador corrige el respaldo (la solicitud enviada lleva su fecha de envío) y reintenta
    gestor.medio.limpiar()
    gestor.respaldar("Usuario.actualizar", json.dumps(corregido_usuario))
    _con_evento_extra(gestor, "SolicitudDominio.insertar", malo | {"fecha_envio": "2026-01-02T00:00:00-05:00"})
    assert admin.post(SINCRONIZACION, {}, format="json").json() == {"sincronizados": 2}
    assert nombre_de(evento_pendiente) == "Laura Nueva"
    assert len(contenedor().solicitudes.buscar_por_solicitante(id_cliente)) == 1
    assert admin.get(PENDIENTES).json() == []


def test_sincronizar_con_la_bd_caida_es_503_y_el_respaldo_queda_intacto(admin, evento_pendiente):
    with mock.patch("chibchaweb.persistencia.transacciones.transaction.atomic", side_effect=OperationalError("sin BD")):
        assert_error(admin.post(SINCRONIZACION, {}, format="json"), 503, "CONTINGENCIA")
    assert len(admin.get(PENDIENTES).json()) == 1


# --- permisos ----------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("verbo", "ruta", "cuerpo"),
    [("get", PENDIENTES, None), ("put", ALGORITMO, {"nombre": "AES"}), ("post", SINCRONIZACION, {})],
)
def test_solo_gestionar_contingencia(anonimo, gestion, soporte, cliente_http, verbo, ruta, cuerpo):
    for http in (gestion, soporte, cliente_http):
        assert_error(getattr(http, verbo)(ruta, cuerpo, format="json"), 403, "SIN_PERMISO")
    assert_error(getattr(anonimo, verbo)(ruta, cuerpo, format="json"), 401, "NO_AUTENTICADO")


# --- D-33: el registro de cliente (usuario + suscripción) con la BD cayendo a mitad ---------------------
@contextmanager
def bd_sin_escrituras_en(modelo):
    """Solo falla el ``save`` de ``modelo``: las escrituras anteriores de la petición sí se hicieron."""
    from django.db.models import Model

    guardar = Model.save

    def save(self, *args, **kwargs):
        if isinstance(self, modelo):
            raise OperationalError("sin BD")
        return guardar(self, *args, **kwargs)

    with mock.patch.object(Model, "save", save):
        yield


def _registrar(correo):
    from rest_framework.test import APIClient

    from tests.web.conftest import cuerpo_registro, entrar

    http = APIClient()
    assert entrar(http, correo).json()["registrado"] is False
    return http.post(f"{BASE}/auth/registro", cuerpo_registro(), format="json")


def test_d32_registro_que_cae_en_la_primera_escritura_deja_un_evento_con_usuario_y_suscripcion(admin):
    from chibchaweb.persistencia.modelos_orm import UsuarioOrm

    with bd_sin_escrituras_en(UsuarioOrm):
        assert_error(_registrar("primero@correo.co"), 503, "CONTINGENCIA")
    assert [e["titulo"] for e in admin.get(PENDIENTES).json()] == ["Usuario.insertar"]
    assert admin.post(SINCRONIZACION, {}, format="json").json() == {"sincronizados": 1}  # autosuficiente
    from chibchaweb.persistencia.modelos_orm import SuscripcionOrm

    assert SuscripcionOrm.objects.filter(sitio__subdominio="tiendalaura.chibchaweb.com").exists()


def test_d32_registro_que_cae_tras_insertar_al_cliente_responde_503_sin_evento_y_sin_filas(admin):
    from chibchaweb.persistencia.modelos_orm import SitioWebOrm, UsuarioOrm

    with bd_sin_escrituras_en(SitioWebOrm):  # el usuario ya se escribió; falla la suscripción
        r = _registrar("segundo@correo.co")
    assert_error(r, 503, "CONTINGENCIA")
    assert "no quedó respaldada" in r.json()["mensaje"]
    assert admin.get(PENDIENTES).json() == []  # sin evento huérfano que bloquee el respaldo
    assert not UsuarioOrm.objects.filter(correo="segundo@correo.co").exists()  # el rollback dejó la BD coherente
    assert admin.post(SINCRONIZACION, {}, format="json").json() == {"sincronizados": 0}
    assert _registrar("segundo@correo.co").status_code == 201  # el reintento funciona
