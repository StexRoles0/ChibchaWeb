"""CU-DOM-01 y CU-DOM-02: ``/dominios/solicitudes`` (api.md §Dominios)."""

from unittest import mock

import pytest
from django.db import OperationalError

from config.contenedor import contenedor
from tests.web.conftest import BASE, assert_error

RUTA = f"{BASE}/dominios/solicitudes"


def solicitar(http, nombre="tiendalaura", extension=".co"):
    return http.post(RUTA, {"nombre": nombre, "extension": extension}, format="json")


# --- DOM-01 + DOM-02 -----------------------------------------------------------------------------
def test_solicitud_valida_responde_201_con_id_y_estado_enviada(cliente_http):
    r = solicitar(cliente_http)
    assert r.status_code == 201
    assert set(r.json()) == {"id", "estado"} and r.json()["estado"] == "ENVIADA"
    (fila,) = cliente_http.get(RUTA).json()
    assert fila["id"] == r.json()["id"] and fila["titulo"] == "tiendalaura.co" and fila["estado"] == "ENVIADA"


def test_rn18_el_registrador_recibe_el_xml_del_anexo(cliente_http):
    with mock.patch.object(contenedor().registrador_dominio, "enviar") as enviar:
        assert solicitar(cliente_http, "TiendaLaura").status_code == 201
    (xml,) = [llamada.args[0] for llamada in enviar.call_args_list]
    assert "<solicitante><nombre>Laura</nombre><correo>laura@correo.co</correo></solicitante>" in xml
    assert "<dominio><nombre>tiendalaura</nombre><extension>.co</extension></dominio>" in xml


def test_registrador_que_rechaza_deja_la_solicitud_fallida_con_201(cliente_http):
    r = solicitar(cliente_http, "rechazo-total", ".com")
    assert r.status_code == 201 and r.json()["estado"] == "FALLIDA"
    assert cliente_http.get(RUTA).json()[0]["estado"] == "FALLIDA"
    assert solicitar(cliente_http, "otra", ".com").json()["estado"] == "ENVIADA"  # puede enviar una nueva


@pytest.mark.parametrize("nombre", ["", "-malo", "malo-", "con espacio", "a" * 64])
def test_nombre_invalido_es_422_y_no_se_guarda(cliente_http, nombre):
    assert_error(solicitar(cliente_http, nombre), 422, "VALIDACION", "nombre")
    assert cliente_http.get(RUTA).json() == []


@pytest.mark.parametrize("extension", [".xyz", "", "."])
def test_extension_no_admitida_es_422_y_no_se_guarda(cliente_http, extension):
    assert_error(solicitar(cliente_http, extension=extension), 422, "VALIDACION", "extension")
    assert cliente_http.get(RUTA).json() == []


def test_cuerpo_incompleto_es_400(cliente_http):
    assert_error(cliente_http.post(RUTA, {"nombre": "x"}, format="json"), 400, "SOLICITUD_INVALIDA", "extension")
    assert_error(cliente_http.post(RUTA, {"extension": ".co"}, format="json"), 400, "SOLICITUD_INVALIDA", "nombre")


def test_contingencia_en_la_escritura_responde_503_y_respalda_el_evento(cliente_http):
    with mock.patch(
        "chibchaweb.persistencia.mapeadores.solicitud.SolicitudDominioOrm.save", side_effect=OperationalError("sin BD")
    ):
        assert_error(solicitar(cliente_http), 503, "CONTINGENCIA")
    pendientes = contenedor().gestor.recuperar_pendientes()
    assert len(pendientes) == 1 and pendientes[0].startswith("SolicitudDominio.insertar|")
    assert cliente_http.get(RUTA).json() == []


# --- consultarSolicitudes ------------------------------------------------------------------------
def test_listado_recientes_primero_con_la_fecha_como_subtitulo(cliente_http):
    primera = solicitar(cliente_http, "primera", ".com").json()["id"]
    segunda = solicitar(cliente_http, "segunda", ".org").json()["id"]
    filas = cliente_http.get(RUTA).json()
    assert [(f["id"], f["titulo"]) for f in filas] == [(segunda, "segunda.org"), (primera, "primera.com")]
    assert all(len(f["subtitulo"]) == 10 and f["subtitulo"][4] == "-" for f in filas)


def test_cada_cliente_ve_solo_las_suyas(cliente_http):
    from tests.web.conftest import cliente_en_sesion

    solicitar(cliente_http)
    otro = cliente_en_sesion("otro@correo.co", sitio="otrositio")
    assert otro.get(RUTA).json() == []


def test_solo_un_cliente_con_sesion_solicita_y_consulta(gestion, soporte, anonimo):
    for http in (gestion, soporte):
        assert_error(solicitar(http), 403, "SIN_PERMISO")
        assert_error(http.get(RUTA), 403, "SIN_PERMISO")
    assert_error(solicitar(anonimo), 401, "NO_AUTENTICADO")
    assert_error(anonimo.get(RUTA), 401, "NO_AUTENTICADO")
