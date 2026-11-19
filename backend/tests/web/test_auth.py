"""CU-AUTH-01, CU-AUTH-02, CU-AUTH-03 y catálogo: endpoints de acceso (api.md §Acceso)."""

import pytest
from rest_framework.test import APIClient

from config.contenedor import contenedor
from tests.web.conftest import BASE, assert_error, cuerpo_registro, entrar

# --- CU-AUTH-01 ----------------------------------------------------------------------------------


def test_inicio_simulado_devuelve_la_url_del_callback_con_state(anonimo):
    r = anonimo.get(f"{BASE}/auth/oauth/inicio", {"correo": "ana@correo.co"})
    assert r.status_code == 200
    url = r.json()["url"]
    assert url.startswith("/auth/callback?code=dev:ana@correo.co&state=")
    assert len(url.split("state=")[1]) >= 32
    assert "csrftoken" in r.cookies  # Angular lo manda en X-CSRFToken


def test_inicio_simulado_sin_correo_es_400(anonimo):
    assert_error(anonimo.get(f"{BASE}/auth/oauth/inicio"), 400, "SOLICITUD_INVALIDA", "correo")


def test_inicio_real_arma_la_url_del_proveedor_sin_pkce(anonimo, settings):
    settings.SIMULAR_EXTERNOS = False
    settings.OIDC_CLIENT_ID = "app-123"
    settings.OIDC_REDIRECT_URI = "http://localhost:4200/auth/callback"
    url = anonimo.get(f"{BASE}/auth/oauth/inicio").json()["url"]
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=app-123" in url and "response_type=code" in url and "state=" in url
    assert "code_challenge" not in url  # P-19 b / D-26


def test_cada_inicio_genera_un_state_distinto(anonimo):
    a = anonimo.get(f"{BASE}/auth/oauth/inicio", {"correo": "a@b.co"}).json()["url"]
    b = anonimo.get(f"{BASE}/auth/oauth/inicio", {"correo": "a@b.co"}).json()["url"]
    assert a != b


# --- CU-AUTH-02 ----------------------------------------------------------------------------------


def test_login_de_empleado_primer_ingreso_vincula_y_trae_rol_y_operaciones(anonimo):
    r = entrar(anonimo, "gestion@chibchaweb.co")  # RN-07: se vincula por correo verificado
    cuerpo = r.json()
    assert r.status_code == 200 and cuerpo["registrado"] is True
    assert (cuerpo["tipoUsuario"], cuerpo["rol"], cuerpo["correo"]) == ("EMPLEADO", "Gestión", "gestion@chibchaweb.co")
    assert set(cuerpo["operaciones"]) == {
        "GESTIONAR_EMPLEADOS", "GESTIONAR_DISTRIBUIDORES", "CONSULTAR_REGISTROS", "REGISTRAR_TICKET",
    }  # fmt: skip
    assert isinstance(cuerpo["idUsuario"], int) and "identificadorExterno" not in cuerpo
    assert entrar(APIClient(), "gestion@chibchaweb.co").json()["idUsuario"] == cuerpo["idUsuario"]  # ahora por sub


@pytest.mark.parametrize(
    ("correo", "rol"),
    [("soporte@chibchaweb.co", "Soporte"), ("admin@chibchaweb.co", "Administrador")],
)
def test_login_de_los_otros_roles(anonimo, correo, rol):
    assert entrar(anonimo, correo).json()["rol"] == rol


def test_login_de_cliente_registrado_no_trae_rol(cliente_http):
    otro = APIClient()
    cuerpo = entrar(otro, "laura@correo.co").json()
    assert cuerpo["registrado"] is True and cuerpo["tipoUsuario"] == "CLIENTE"
    assert cuerpo["operaciones"] == [] and "rol" not in cuerpo and cuerpo["idUsuario"] == cliente_http.id_usuario


def test_fa2_usuario_nuevo_devuelve_datos_para_prellenar_y_no_serializa_el_sub(anonimo):
    r = entrar(anonimo, "laura.gomez@correo.co")
    assert r.status_code == 200
    assert r.json() == {
        "registrado": False,
        "nombre": "Laura Gomez",
        "correo": "laura.gomez@correo.co",
        "tipoUsuario": "",
        "operaciones": [],
    }
    assert "dev|" not in r.content.decode()
    assert anonimo.get(f"{BASE}/auth/sesion").status_code == 401  # aún no es una sesión autenticada


def test_rn07_correo_no_verificado_no_vincula_y_se_trata_como_nuevo(anonimo):
    r = entrar(anonimo, "gestion@chibchaweb.co", prefijo="dev-noverificado")
    assert r.json()["registrado"] is False
    assert contenedor().usuarios.buscar_por_correo("gestion@chibchaweb.co").cuenta is None


def test_fa3_usuario_inactivo_es_403(anonimo):
    entrar(APIClient(), "soporte@chibchaweb.co")  # vincula
    usuarios = contenedor().usuarios
    empleado = usuarios.buscar_por_correo("soporte@chibchaweb.co")
    empleado.inactivar()
    usuarios.actualizar(empleado)
    assert_error(entrar(anonimo, "soporte@chibchaweb.co"), 403, "USUARIO_INACTIVO")
    assert anonimo.get(f"{BASE}/auth/sesion").status_code == 401


def test_fa3_codigo_invalido_es_401_autorizacion_fallida(anonimo):
    estado = anonimo.get(f"{BASE}/auth/oauth/inicio", {"correo": "a@b.co"}).json()["url"].split("state=")[1]
    r = anonimo.post(f"{BASE}/auth/oauth/callback", {"codigo": "no-es-valido", "estado": estado}, format="json")
    assert_error(r, 401, "AUTORIZACION_FALLIDA")


def test_fa3_state_distinto_es_401_y_el_original_queda_consumido(anonimo):
    anonimo.get(f"{BASE}/auth/oauth/inicio", {"correo": "a@b.co"})
    r = anonimo.post(f"{BASE}/auth/oauth/callback", {"codigo": "dev:a@b.co", "estado": "falso"}, format="json")
    assert_error(r, 401, "AUTORIZACION_FALLIDA")
    r = anonimo.post(f"{BASE}/auth/oauth/callback", {"codigo": "dev:a@b.co", "estado": "falso"}, format="json")
    assert_error(r, 401, "AUTORIZACION_FALLIDA")  # sin state en la sesión


def test_el_state_es_de_un_solo_uso(anonimo):
    url = anonimo.get(f"{BASE}/auth/oauth/inicio", {"correo": "ana@b.co"}).json()["url"]
    estado = url.split("state=")[1]
    cuerpo = {"codigo": "dev:ana@b.co", "estado": estado}
    assert anonimo.post(f"{BASE}/auth/oauth/callback", cuerpo, format="json").status_code == 200
    assert_error(anonimo.post(f"{BASE}/auth/oauth/callback", cuerpo, format="json"), 401, "AUTORIZACION_FALLIDA")


def test_callback_sin_inicio_previo_es_401(anonimo):
    r = anonimo.post(f"{BASE}/auth/oauth/callback", {"codigo": "dev:a@b.co", "estado": "x"}, format="json")
    assert_error(r, 401, "AUTORIZACION_FALLIDA")


def test_callback_con_cuerpo_incompleto_es_400(anonimo):
    assert_error(
        anonimo.post(f"{BASE}/auth/oauth/callback", {"codigo": "x"}, format="json"), 400, "SOLICITUD_INVALIDA", "estado"
    )


def test_callback_con_json_mal_formado_es_400(anonimo):
    r = anonimo.post(f"{BASE}/auth/oauth/callback", "{no es json", content_type="application/json")
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


# --- sesión y logout -----------------------------------------------------------------------------


def test_sesion_devuelve_el_resultado_de_acceso_guardado(gestion):
    r = gestion.get(f"{BASE}/auth/sesion")
    assert r.status_code == 200 and r.json()["rol"] == "Gestión" and r.json()["registrado"] is True
    assert r.json()["correo"] == "gestion@chibchaweb.co" and "GESTIONAR_EMPLEADOS" in r.json()["operaciones"]


def test_sesion_y_logout_sin_sesion_son_401(anonimo):
    assert_error(anonimo.get(f"{BASE}/auth/sesion"), 401, "NO_AUTENTICADO")
    assert_error(anonimo.post(f"{BASE}/auth/logout"), 401, "NO_AUTENTICADO")


def test_logout_cierra_la_sesion(gestion):
    assert gestion.post(f"{BASE}/auth/logout").status_code == 204
    assert_error(gestion.get(f"{BASE}/auth/sesion"), 401, "NO_AUTENTICADO")


def test_cancelar_el_registro_descarta_la_identidad_pendiente(anonimo):
    entrar(anonimo, "nuevo@correo.co")
    assert anonimo.post(f"{BASE}/auth/logout").status_code == 204
    assert_error(anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(), format="json"), 401, "NO_AUTENTICADO")


def test_iniciar_sesion_rota_la_clave_de_sesion(anonimo):
    anonimo.get(f"{BASE}/auth/oauth/inicio", {"correo": "gestion@chibchaweb.co"})
    antes = anonimo.cookies["sessionid"].value
    url = anonimo.get(f"{BASE}/auth/oauth/inicio", {"correo": "gestion@chibchaweb.co"}).json()["url"]
    anonimo.post(
        f"{BASE}/auth/oauth/callback",
        {"codigo": "dev:gestion@chibchaweb.co", "estado": url.split("state=")[1]},
        format="json",
    )
    assert anonimo.cookies["sessionid"].value != antes


# --- CSRF (D-04, D-17) ---------------------------------------------------------------------------


def test_csrf_se_exige_en_los_verbos_que_escriben_con_sesion():
    http = APIClient(enforce_csrf_checks=True)
    url = http.get(f"{BASE}/auth/oauth/inicio", {"correo": "gestion@chibchaweb.co"}).json()["url"]
    token = http.cookies["csrftoken"].value
    cuerpo = {"codigo": "dev:gestion@chibchaweb.co", "estado": url.split("state=")[1]}
    r = http.post(f"{BASE}/auth/oauth/callback", cuerpo, format="json")  # hay state en la sesión: exige CSRF
    assert_error(r, 403, "SIN_PERMISO")
    estado = http.get(f"{BASE}/auth/oauth/inicio", {"correo": "gestion@chibchaweb.co"}).json()["url"].split("state=")[1]
    r = http.post(
        f"{BASE}/auth/oauth/callback", {**cuerpo, "estado": estado}, format="json", headers={"X-CSRFToken": token}
    )
    assert r.status_code == 200
    token = http.cookies["csrftoken"].value
    assert_error(http.post(f"{BASE}/auth/logout"), 403, "SIN_PERMISO")
    assert http.get(f"{BASE}/auth/sesion").status_code == 200  # los GET no lo exigen
    assert http.post(f"{BASE}/auth/logout", headers={"X-CSRFToken": token}).status_code == 204


# --- CU-AUTH-03 ----------------------------------------------------------------------------------


def test_registro_crea_la_cuenta_abre_sesion_y_el_perfil_es_consultable(anonimo):
    entrar(anonimo, "laura@correo.co")
    r = anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(nombre="Laura Gómez"), format="json")
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["registrado"] is True and cuerpo["tipoUsuario"] == "CLIENTE" and cuerpo["nombre"] == "Laura Gómez"
    assert cuerpo["correo"] == "laura@correo.co" and cuerpo["operaciones"] == []
    assert anonimo.get(f"{BASE}/auth/sesion").json()["idUsuario"] == cuerpo["idUsuario"]
    perfil = anonimo.get(f"{BASE}/clientes/me").json()
    assert "sitio: tiendalaura.chibchaweb.com" in perfil["campos"]  # RN-14 / P-15
    assert "montoPeriodo: 54.00" in perfil["campos"] and "tarjeta: VISA •••• 4242" in perfil["campos"]  # RN-01, RN-12
    assert entrar(APIClient(), "laura@correo.co").json()["idUsuario"] == cuerpo["idUsuario"]  # cuenta vinculada


def test_registro_toma_el_nombre_de_la_identidad_si_no_viene(anonimo):
    entrar(anonimo, "laura.gomez@correo.co")
    r = anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(), format="json")
    assert r.status_code == 201 and r.json()["nombre"] == "Laura Gomez"


def test_registro_ignora_identidad_y_correo_enviados_por_el_cliente(anonimo):
    entrar(anonimo, "laura@correo.co")
    r = anonimo.post(
        f"{BASE}/auth/registro",
        cuerpo_registro(identificadorExterno="dev|otro@x.co", correo="otro@x.co"),
        format="json",
    )
    assert r.status_code == 201 and r.json()["correo"] == "laura@correo.co"


def test_registro_con_codigo_de_distribuidor_valido(anonimo, gestion):
    entrar(anonimo, "laura@correo.co")
    assert (
        anonimo.post(
            f"{BASE}/auth/registro", cuerpo_registro(codigoDistribuidor="DIS-ANDES1"), format="json"
        ).status_code
        == 201
    )
    (distribuidor,) = gestion.get(f"{BASE}/consultas/DISTRIBUIDOR", {"filtro": "andes"}).json()
    assert distribuidor["subtitulo"].endswith("1 referidos")  # RN-13


def test_registro_sin_identidad_pendiente_es_401(anonimo):
    assert_error(anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(), format="json"), 401, "NO_AUTENTICADO")


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"numeroTarjeta": "4242424242420002"}, "numeroTarjeta"),  # validador externo (D-06)
        ({"numeroTarjeta": "5105105105105100"}, "numeroTarjeta"),  # no es VISA
        ({"vencimiento": "2020-01-01"}, "vencimiento"),
        ({"codigoSeguridad": "12"}, "codigoSeguridad"),
        ({"franquicia": "AMEX"}, "franquicia"),
        ({"idPaquete": 99}, "idPaquete"),
        ({"idPlan": 99}, "idPlan"),
        ({"plataforma": "MAC"}, "plataforma"),
        ({"sitio": "no valido!"}, "sitio"),
        ({"lineaResidencia": ""}, "lineaResidencia"),
        ({"codigoPostalFacturacion": "1"}, "lineaFacturacion"),
        ({"telefono": "abc"}, "telefono"),
        ({"codigoDistribuidor": "DIS-NOEXIS"}, "codigoDistribuidor"),
    ],
)
def test_registro_con_datos_invalidos_es_422_con_campo_y_no_guarda(anonimo, cambios, campo):
    entrar(anonimo, "laura@correo.co")
    r = anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(**cambios), format="json")
    assert_error(r, 422, "VALIDACION", campo)
    assert contenedor().usuarios.buscar_por_correo("laura@correo.co") is None
    assert anonimo.get(f"{BASE}/auth/sesion").status_code == 401  # sigue pendiente, sin sesión


def test_registro_con_la_identidad_pendiente_intacta_permite_reintentar(anonimo):
    entrar(anonimo, "laura@correo.co")
    assert (
        anonimo.post(
            f"{BASE}/auth/registro", cuerpo_registro(numeroTarjeta="4242424242420002"), format="json"
        ).status_code
        == 422
    )
    assert anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(), format="json").status_code == 201


def test_registro_con_subdominio_ocupado_es_409_y_se_revierte_todo(cliente_http, anonimo):
    entrar(anonimo, "pedro@correo.co")
    r = anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(sitio="TiendaLaura"), format="json")
    assert_error(r, 409, "SUBDOMINIO_EN_USO", "sitio")
    assert contenedor().usuarios.buscar_por_correo("pedro@correo.co") is None  # el cliente tampoco quedó


def test_registro_con_correo_de_un_empleado_sin_verificar_es_409_duplicado(anonimo):
    entrar(anonimo, "gestion@chibchaweb.co", prefijo="dev-noverificado")  # no se vincula: queda pendiente
    r = anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(), format="json")
    assert_error(r, 409, "DUPLICADO", "correo")


def test_un_usuario_con_sesion_no_puede_volver_a_registrarse(cliente_http):
    assert_error(cliente_http.post(f"{BASE}/auth/registro", cuerpo_registro(), format="json"), 403, "SIN_PERMISO")


@pytest.mark.parametrize("campo", ["idPaquete", "numeroTarjeta", "vencimiento", "franquicia"])
def test_registro_con_campos_faltantes_es_400(anonimo, campo):
    entrar(anonimo, "laura@correo.co")
    r = anonimo.post(f"{BASE}/auth/registro", {k: v for k, v in cuerpo_registro().items() if k != campo}, format="json")
    assert_error(r, 400, "SOLICITUD_INVALIDA", campo)


def test_registro_con_tipos_incorrectos_es_400(anonimo):
    entrar(anonimo, "laura@correo.co")
    assert_error(
        anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(idPaquete="dos"), format="json"),
        400,
        "SOLICITUD_INVALIDA",
        "idPaquete",
    )
    assert_error(
        anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(vencimiento="12/30"), format="json"),
        400,
        "SOLICITUD_INVALIDA",
        "vencimiento",
    )


def test_el_codigo_de_seguridad_no_se_guarda_ni_se_devuelve(anonimo):
    entrar(anonimo, "laura@correo.co")
    r = anonimo.post(f"{BASE}/auth/registro", cuerpo_registro(codigoSeguridad="987"), format="json")
    assert "987" not in r.content.decode()
    perfil = anonimo.get(f"{BASE}/clientes/me").content.decode()
    assert "987" not in perfil and "4242424242424242" not in perfil


# --- catálogo ------------------------------------------------------------------------------------


def test_catalogo_publico_de_paquetes_y_planes(anonimo):
    paquetes = anonimo.get(f"{BASE}/catalogo/paquetes")
    planes = anonimo.get(f"{BASE}/catalogo/planes")
    assert [(p["titulo"], p["subtitulo"]) for p in paquetes.json()] == [
        ("Chibcha-Plata", "5.00"), ("Chibcha-Oro", "10.00"), ("Chibcha-Platino", "20.00"),
    ]  # fmt: skip
    assert [p["subtitulo"] for p in planes.json()] == ["1|0.00", "3|0.05", "6|0.10", "12|0.15"]
    assert set(paquetes.json()[0]) == {"id", "titulo", "subtitulo", "estado"}


def test_catalogo_de_roles_exige_gestionar_empleados(gestion, soporte, cliente_http, anonimo):
    assert [r["titulo"] for r in gestion.get(f"{BASE}/catalogo/roles").json()] == [
        "Gestión",
        "Soporte",
        "Administrador",
    ]
    assert_error(soporte.get(f"{BASE}/catalogo/roles"), 403, "SIN_PERMISO")
    assert_error(cliente_http.get(f"{BASE}/catalogo/roles"), 403, "SIN_PERMISO")
    assert_error(anonimo.get(f"{BASE}/catalogo/roles"), 401, "NO_AUTENTICADO")
