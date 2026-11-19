"""CU-CLI-01, CU-CLI-02, CU-CLI-03 y consultarSitios: ``/clientes/me`` (api.md §Clientes)."""

import pytest

from config.contenedor import contenedor
from tests.web.conftest import BASE, assert_error, cliente_en_sesion, entrar

ME = f"{BASE}/clientes/me"


def pago(**cambios):
    cuerpo = {
        "numeroTarjeta": "5105105105105100", "vencimiento": "2099-01-01", "codigoSeguridad": "123",
        "franquicia": "MASTERCARD", "lineaFacturacion": "Av 1", "ciudadFacturacion": "X",
        "codigoPostalFacturacion": "050001",
    }  # fmt: skip
    cuerpo.update(cambios)
    return {k: v for k, v in cuerpo.items() if v is not None}


def campos(respuesta) -> dict[str, str]:
    return dict(c.split(": ", 1) for c in respuesta.json()["campos"])


# --- CLI-01 --------------------------------------------------------------------------------------
def test_perfil_trae_el_detalle_del_cliente_de_la_sesion(cliente_http):
    r = cliente_http.get(ME)
    assert r.status_code == 200 and r.json()["id"] == cliente_http.id_usuario and r.json()["titulo"] == "Laura"
    c = campos(r)
    assert c["correo"] == "laura@correo.co" and c["activo"] == "true" and c["plan"] == "Semestral"
    assert c["idSuscripcion"].isdigit() and c["fechaCorte"] and c["distribuidor"] == ""


def test_perfil_solo_muestra_al_propio_cliente():
    a = cliente_en_sesion("a@correo.co", sitio="sitioa")
    b = cliente_en_sesion("b@correo.co", sitio="sitiob")
    assert campos(a.get(ME))["correo"] == "a@correo.co" and campos(b.get(ME))["correo"] == "b@correo.co"


def test_perfil_exige_ser_cliente(anonimo, gestion):
    assert_error(anonimo.get(ME), 401, "NO_AUTENTICADO")
    assert_error(gestion.get(ME), 403, "SIN_PERMISO")
    assert_error(gestion.patch(f"{ME}?categoria=PERSONAL", {}, format="json"), 403, "SIN_PERMISO")
    assert_error(gestion.delete(ME), 403, "SIN_PERMISO")


# --- CLI-03 --------------------------------------------------------------------------------------
def test_modificar_personal(cliente_http):
    r = cliente_http.patch(
        f"{ME}?categoria=PERSONAL",
        {
            "nombre": "Laura G.",
            "telefono": "3109998888",
            "ciudadResidencia": "Cali",
            "sitio": "nuevositio",
            "plataforma": "WINDOWS",
        },
        format="json",
    )
    assert r.status_code == 204 and not r.content
    c = campos(cliente_http.get(ME))
    assert (c["nombre"], c["telefono"], c["ciudadResidencia"]) == ("Laura G.", "3109998888", "Cali")
    assert (c["sitio"], c["plataforma"], c["correo"]) == ("nuevositio.chibchaweb.com", "WINDOWS", "laura@correo.co")


def test_modificar_personal_acepta_el_subdominio_completo_del_detalle(cliente_http):
    cuerpo = {"sitio": campos(cliente_http.get(ME))["sitio"]}
    assert cliente_http.patch(f"{ME}?categoria=PERSONAL", cuerpo, format="json").status_code == 204
    assert campos(cliente_http.get(ME))["sitio"] == "tiendalaura.chibchaweb.com"


def test_modificar_paquete_y_plan_no_mueve_el_corte(cliente_http):
    antes = campos(cliente_http.get(ME))
    r = cliente_http.patch(
        f"{ME}?categoria=PAQUETE_PLAN",
        {"idSuscripcion": int(antes["idSuscripcion"]), "idPaquete": 3, "idPlan": 4},
        format="json",
    )
    assert r.status_code == 204
    despues = campos(cliente_http.get(ME))
    assert (despues["paquete"], despues["plan"], despues["montoPeriodo"]) == ("Chibcha-Platino", "Anual", "204.00")
    assert despues["fechaCorte"] == antes["fechaCorte"]


def test_modificar_pago_reemplaza_tarjeta_y_direccion(cliente_http):
    cuerpo = {
        "lineaFacturacion": "Av 68 # 10-10", "ciudadFacturacion": "Medellín", "codigoPostalFacturacion": "050001",
        "numeroTarjeta": "5105105105105100", "vencimiento": "2099-01-01", "codigoSeguridad": "8642",
        "franquicia": "MASTERCARD",
    }  # fmt: skip
    assert cliente_http.patch(f"{ME}?categoria=PAGO", cuerpo, format="json").status_code == 204
    r = cliente_http.get(ME)
    c = campos(r)
    assert (c["tarjeta"], c["franquicia"], c["ciudadFacturacion"], c["vencimiento"]) == (
        "MASTERCARD •••• 5100", "MASTERCARD", "Medellín", "2099-01-01",
    )  # fmt: skip
    assert "8642" not in r.content.decode() and "5105105105105100" not in r.content.decode()  # RN-12


@pytest.mark.parametrize(
    ("categoria", "cuerpo", "campo"),
    [
        ("PERSONAL", {"nombre": ""}, "nombre"),
        ("PERSONAL", {"telefono": "abc"}, "telefono"),
        ("PERSONAL", {"codigoPostalResidencia": "1"}, "lineaResidencia"),
        ("PERSONAL", {"sitio": "no valido!"}, "sitio"),
        ("PAQUETE_PLAN", {"idPaquete": 3}, "idSuscripcion"),
        ("PAQUETE_PLAN", {"idSuscripcion": 1}, "idPaquete"),
        ("PAGO", pago(numeroTarjeta="5105105105100002"), "numeroTarjeta"),
        ("PAGO", pago(vencimiento="2020-01-01"), "vencimiento"),
        ("PAGO", pago(codigoSeguridad=None), "codigoSeguridad"),  # D-22: la tarjeta se reingresa completa
        ("PAGO", pago(lineaFacturacion=""), "lineaFacturacion"),
    ],
)  # fmt: skip
def test_modificar_con_datos_invalidos_es_422_y_no_cambia_nada(cliente_http, categoria, cuerpo, campo):
    antes = cliente_http.get(ME).json()
    assert_error(cliente_http.patch(f"{ME}?categoria={categoria}", cuerpo, format="json"), 422, "VALIDACION", campo)
    assert cliente_http.get(ME).json() == antes


def test_modificar_paquete_plan_de_una_suscripcion_ajena_es_404(cliente_http):
    r = cliente_http.patch(f"{ME}?categoria=PAQUETE_PLAN", {"idSuscripcion": 99999, "idPlan": 1}, format="json")
    assert_error(r, 404, "NO_ENCONTRADO")


def test_modificar_personal_con_subdominio_ocupado_es_409():
    cliente_en_sesion("a@correo.co", sitio="sitioa")
    b = cliente_en_sesion("b@correo.co", sitio="sitiob")
    assert_error(
        b.patch(f"{ME}?categoria=PERSONAL", {"sitio": "sitioa"}, format="json"), 409, "SUBDOMINIO_EN_USO", "sitio"
    )
    assert campos(b.get(ME))["sitio"] == "sitiob.chibchaweb.com"


@pytest.mark.parametrize("query", ["", "?categoria=OTRA", "?categoria="])
def test_modificar_sin_categoria_valida_es_400(cliente_http, query):
    assert_error(
        cliente_http.patch(f"{ME}{query}", {"telefono": "1"}, format="json"), 400, "SOLICITUD_INVALIDA", "categoria"
    )


def test_modificar_con_tipos_incorrectos_es_400(cliente_http):
    assert_error(
        cliente_http.patch(f"{ME}?categoria=PAQUETE_PLAN", {"idPaquete": "tres"}, format="json"),
        400,
        "SOLICITUD_INVALIDA",
        "idPaquete",
    )


# --- CLI-02 --------------------------------------------------------------------------------------
def test_eliminar_perfil_inactiva_suspende_y_cierra_la_sesion(cliente_http, anonimo):
    assert cliente_http.delete(ME).status_code == 204
    assert_error(cliente_http.get(ME), 401, "NO_AUTENTICADO")  # la sesión se cerró
    assert_error(entrar(anonimo, "laura@correo.co"), 403, "USUARIO_INACTIVO")  # RN-09
    cliente = contenedor().usuarios.buscar_por_correo("laura@correo.co")
    assert not cliente.activo and all(not s.activa for s in cliente.suscripciones)


def test_eliminar_perfil_dos_veces_no_se_puede_sin_sesion(cliente_http):
    cliente_http.delete(ME)
    assert_error(cliente_http.delete(ME), 401, "NO_AUTENTICADO")


def test_eliminar_perfil_ya_inactivo_es_idempotente(cliente_http):
    usuarios = contenedor().usuarios
    cliente = usuarios.buscar_por_correo("laura@correo.co")
    cliente.inactivar()
    usuarios.actualizar(cliente)
    assert cliente_http.delete(ME).status_code == 204  # la sesión aún era válida


def test_un_cliente_inactivo_con_sesion_abierta_no_modifica_su_perfil(cliente_http):
    usuarios = contenedor().usuarios
    cliente = usuarios.buscar_por_correo("laura@correo.co")
    cliente.inactivar()
    usuarios.actualizar(cliente)
    assert_error(
        cliente_http.patch(f"{ME}?categoria=PERSONAL", {"telefono": "1"}, format="json"), 403, "USUARIO_INACTIVO"
    )


# --- sitios (P-06) -------------------------------------------------------------------------------
def test_sitios_del_cliente(cliente_http, anonimo, gestion):
    r = cliente_http.get(f"{ME}/sitios")
    assert r.status_code == 200
    (sitio,) = r.json()
    assert sitio["titulo"] == "tiendalaura.chibchaweb.com" and sitio["subtitulo"] == "UNIX · Chibcha-Oro"
    assert sitio["estado"] == "ACTIVA" and isinstance(sitio["id"], int)
    assert_error(anonimo.get(f"{ME}/sitios"), 401, "NO_AUTENTICADO")
    assert_error(gestion.get(f"{ME}/sitios"), 403, "SIN_PERMISO")


def test_rn05_el_correo_del_cuerpo_no_cambia_el_correo_del_cliente(cliente_http):
    r = cliente_http.patch(
        f"{ME}?categoria=PERSONAL", {"nombre": "Laura B.", "correo": "otro@correo.co"}, format="json"
    )
    assert r.status_code == 204, r.content
    c = campos(cliente_http.get(ME))
    assert c["correo"] == "laura@correo.co"
    assert cliente_http.get(ME).json()["titulo"] == "Laura B."
