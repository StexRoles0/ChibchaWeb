"""CU-DIS-01..04: ``/distribuidores`` (api.md §Empleados y distribuidores)."""

import re

import pytest

from tests.web.conftest import BASE, assert_error, cliente_en_sesion

NUEVO = {
    "nombre": "Sur Digital",
    "documento": "800111222",
    "correo": "Contacto@SurDigital.co",
    "telefono": "6017778899",
}


def cuerpo(**cambios):
    return {**NUEVO, **cambios}


def crear(gestion, **cambios):
    r = gestion.post(f"{BASE}/distribuidores", cuerpo(**cambios), format="json")
    assert r.status_code == 201, r.content
    return r.json()


def campos(r) -> dict[str, str]:
    return dict(c.split(": ", 1) for c in r.json()["campos"])


# --- DIS-01 --------------------------------------------------------------------------------------
def test_listar_distribuidores_con_filtro(gestion):
    (d,) = gestion.get(f"{BASE}/distribuidores").json()
    assert d["titulo"] == "Andes Digital SAS" and d["subtitulo"] == "900123456 · DIS-ANDES1 · 0 referidos"
    assert gestion.get(f"{BASE}/distribuidores", {"filtro": "andes1"}).json() == [d]
    assert gestion.get(f"{BASE}/distribuidores", {"filtro": "zzz"}).json() == []


def test_detalle_de_distribuidor_e_inexistente(gestion, cliente_http):
    (d,) = gestion.get(f"{BASE}/distribuidores").json()
    r = gestion.get(f"{BASE}/distribuidores/{d['id']}")
    assert r.status_code == 200 and campos(r)["codigo"] == "DIS-ANDES1" and campos(r)["categoria"] == "Básico"
    assert_error(gestion.get(f"{BASE}/distribuidores/999999"), 404, "NO_ENCONTRADO")
    assert_error(gestion.get(f"{BASE}/distribuidores/{cliente_http.id_usuario}"), 404, "NO_ENCONTRADO")


def test_solo_gestion_administra_distribuidores(soporte, admin, cliente_http, anonimo, gestion):
    nuevo = crear(gestion)
    pedidos = [
        ("get", f"{BASE}/distribuidores", None),
        ("post", f"{BASE}/distribuidores", cuerpo()),
        ("get", f"{BASE}/distribuidores/{nuevo['id']}", None),
        ("put", f"{BASE}/distribuidores/{nuevo['id']}", cuerpo()),
        ("delete", f"{BASE}/distribuidores/{nuevo['id']}", None),
    ]
    for verbo, ruta, datos in pedidos:
        extra = {"data": datos, "format": "json"} if datos else {}
        for http in (soporte, admin, cliente_http):
            assert_error(getattr(http, verbo)(ruta, **extra), 403, "SIN_PERMISO")
        assert_error(getattr(anonimo, verbo)(ruta, **extra), 401, "NO_AUTENTICADO")


# --- DIS-02 (RN-15) ------------------------------------------------------------------------------
def test_rn15_crear_distribuidor_devuelve_id_y_codigo_generado(gestion):
    nuevo = crear(gestion)
    assert set(nuevo) == {"id", "codigo"} and re.fullmatch(r"DIS-[A-Z0-9]{6}", nuevo["codigo"])
    detalle = campos(gestion.get(f"{BASE}/distribuidores/{nuevo['id']}"))
    assert (detalle["codigo"], detalle["activo"], detalle["correo"]) == (
        nuevo["codigo"],
        "true",
        "contacto@surdigital.co",
    )
    assert nuevo["codigo"] in gestion.get(f"{BASE}/distribuidores", {"filtro": "800111222"}).json()[0]["subtitulo"]


def test_rn15_dos_distribuidores_tienen_codigos_distintos(gestion):
    a = crear(gestion)
    b = crear(gestion, documento="800333444", correo="otro@surdigital.co")
    assert a["codigo"] != b["codigo"]


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"nombre": ""}, "nombre"),
        ({"correo": "x"}, "correo"),
        ({"telefono": "a"}, "telefono"),
        ({"documento": "!"}, "documento"),
    ],
)
def test_crear_distribuidor_con_datos_invalidos_es_422(gestion, cambios, campo):
    assert_error(gestion.post(f"{BASE}/distribuidores", cuerpo(**cambios), format="json"), 422, "VALIDACION", campo)
    assert len(gestion.get(f"{BASE}/distribuidores").json()) == 1


def test_crear_distribuidor_con_cuerpo_incompleto_es_400(gestion):
    sin_documento = {k: v for k, v in NUEVO.items() if k != "documento"}
    assert_error(
        gestion.post(f"{BASE}/distribuidores", sin_documento, format="json"), 400, "SOLICITUD_INVALIDA", "documento"
    )


def test_crear_distribuidor_duplicado_es_409(gestion):
    crear(gestion)
    assert_error(
        gestion.post(f"{BASE}/distribuidores", cuerpo(documento="1"), format="json"), 409, "DUPLICADO", "correo"
    )
    assert_error(
        gestion.post(f"{BASE}/distribuidores", cuerpo(correo="x@y.co"), format="json"), 409, "DUPLICADO", "documento"
    )
    assert_error(  # el correo es único entre todos los usuarios
        gestion.post(f"{BASE}/distribuidores", cuerpo(correo="soporte@chibchaweb.co", documento="2"), format="json"),
        409, "DUPLICADO", "correo",
    )  # fmt: skip


def test_el_codigo_generado_sirve_en_el_registro_de_un_cliente(gestion):
    nuevo = crear(gestion)
    cliente_en_sesion("referido@correo.co", sitio="referido", codigoDistribuidor=nuevo["codigo"])
    assert (
        f"{nuevo['codigo']} · 1 referidos"
        in gestion.get(f"{BASE}/distribuidores", {"filtro": nuevo["codigo"]}).json()[0]["subtitulo"]
    )


# --- DIS-03 --------------------------------------------------------------------------------------
def test_modificar_distribuidor_204_y_el_codigo_no_cambia(gestion):
    nuevo = crear(gestion)
    r = gestion.put(
        f"{BASE}/distribuidores/{nuevo['id']}", cuerpo(nombre="Sur Digital SAS", telefono="6010000000"), format="json"
    )
    assert r.status_code == 204 and not r.content
    detalle = campos(gestion.get(f"{BASE}/distribuidores/{nuevo['id']}"))
    assert (detalle["nombre"], detalle["telefono"], detalle["codigo"]) == (
        "Sur Digital SAS",
        "6010000000",
        nuevo["codigo"],
    )


def test_modificar_distribuidor_con_datos_de_otro_o_invalidos(gestion):
    nuevo = crear(gestion)
    assert_error(
        gestion.put(f"{BASE}/distribuidores/{nuevo['id']}", cuerpo(documento="900123456"), format="json"),
        409, "DUPLICADO", "documento",
    )  # fmt: skip
    assert_error(
        gestion.put(f"{BASE}/distribuidores/{nuevo['id']}", cuerpo(correo="soporte@chibchaweb.co"), format="json"),
        409, "DUPLICADO", "correo",
    )  # fmt: skip
    assert_error(
        gestion.put(f"{BASE}/distribuidores/{nuevo['id']}", cuerpo(telefono="x"), format="json"),
        422,
        "VALIDACION",
        "telefono",
    )


def test_modificar_distribuidor_inexistente_404_e_inactivo_409(gestion):
    assert_error(gestion.put(f"{BASE}/distribuidores/999999", cuerpo(), format="json"), 404, "NO_ENCONTRADO")
    nuevo = crear(gestion)
    gestion.delete(f"{BASE}/distribuidores/{nuevo['id']}")
    assert_error(gestion.put(f"{BASE}/distribuidores/{nuevo['id']}", cuerpo(), format="json"), 409, "ESTADO_INVALIDO")


# --- DIS-04 --------------------------------------------------------------------------------------
def test_eliminar_distribuidor_es_baja_logica_204_e_idempotente(gestion):
    nuevo = crear(gestion)
    r = gestion.delete(f"{BASE}/distribuidores/{nuevo['id']}")
    assert r.status_code == 204 and not r.content
    assert campos(gestion.get(f"{BASE}/distribuidores/{nuevo['id']}"))["activo"] == "false"
    assert gestion.delete(f"{BASE}/distribuidores/{nuevo['id']}").status_code == 204


def test_un_distribuidor_dado_de_baja_ya_no_sirve_como_codigo_de_referido_rn13(gestion, anonimo):
    from tests.web.conftest import cuerpo_registro, entrar

    nuevo = crear(gestion)
    gestion.delete(f"{BASE}/distribuidores/{nuevo['id']}")
    entrar(anonimo, "tarde@correo.co")
    r = anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(codigoDistribuidor=nuevo["codigo"]), format="json")
    assert_error(r, 422, "VALIDACION", "codigoDistribuidor")


def test_eliminar_distribuidor_inexistente_o_de_otro_tipo_es_404(gestion, cliente_http):
    assert_error(gestion.delete(f"{BASE}/distribuidores/999999"), 404, "NO_ENCONTRADO")
    assert_error(gestion.delete(f"{BASE}/distribuidores/{cliente_http.id_usuario}"), 404, "NO_ENCONTRADO")
