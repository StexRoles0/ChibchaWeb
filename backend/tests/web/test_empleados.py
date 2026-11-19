"""CU-EMP-01..04: ``/empleados`` (api.md §Empleados y distribuidores) y sesiones de empleados dados de baja."""

import pytest

from tests.web.conftest import BASE, assert_error, empleado_en_sesion

NUEVO = {
    "nombre": "Elena Ruiz",
    "documento": "E-2001",
    "correo": "Elena@Chibchaweb.co",
    "telefono": "3005551122",
    "idRol": 2,
}


def cuerpo(**cambios):
    return {**NUEVO, **cambios}


def crear(gestion, **cambios):
    r = gestion.post(f"{BASE}/empleados", cuerpo(**cambios), format="json")
    assert r.status_code == 201, r.content
    return r.json()["id"]


def campos(r) -> dict[str, str]:
    return dict(c.split(": ", 1) for c in r.json()["campos"])


# --- EMP-01 --------------------------------------------------------------------------------------
def test_listar_empleados_con_filtro(gestion):
    todos = gestion.get(f"{BASE}/empleados").json()
    assert {e["titulo"] for e in todos} == {"Gabriela Gestión", "Sergio Soporte", "Ana Administra"}
    (soporte,) = gestion.get(f"{BASE}/empleados", {"filtro": "SERGIO"}).json()
    assert soporte["subtitulo"] == "E-1002 · Soporte" and soporte["estado"] == "ACTIVO"
    assert gestion.get(f"{BASE}/empleados", {"filtro": "zzz"}).json() == []


def test_detalle_de_empleado(gestion):
    (e,) = gestion.get(f"{BASE}/empleados", {"filtro": "E-1001"}).json()
    r = gestion.get(f"{BASE}/empleados/{e['id']}")
    assert r.status_code == 200 and campos(r)["rol"] == "Gestión" and campos(r)["activo"] == "true"


def test_detalle_de_un_no_empleado_o_inexistente_es_404(gestion, cliente_http):
    assert_error(gestion.get(f"{BASE}/empleados/{cliente_http.id_usuario}"), 404, "NO_ENCONTRADO")
    assert_error(gestion.get(f"{BASE}/empleados/999999"), 404, "NO_ENCONTRADO")


def test_solo_gestion_administra_empleados(soporte, admin, cliente_http, anonimo, gestion):
    id = crear(gestion)
    pedidos = [
        ("get", f"{BASE}/empleados", None),
        ("post", f"{BASE}/empleados", cuerpo(documento="E-3", correo="otro@chibchaweb.co")),
        ("get", f"{BASE}/empleados/{id}", None),
        ("put", f"{BASE}/empleados/{id}", cuerpo()),
        ("delete", f"{BASE}/empleados/{id}", None),
    ]
    for verbo, ruta, datos in pedidos:
        for http in (soporte, admin, cliente_http):
            r = getattr(http, verbo)(ruta, **({"data": datos, "format": "json"} if datos else {}))
            assert_error(r, 403, "SIN_PERMISO")
        r = getattr(anonimo, verbo)(ruta, **({"data": datos, "format": "json"} if datos else {}))
        assert_error(r, 401, "NO_AUTENTICADO")


# --- EMP-02 --------------------------------------------------------------------------------------
def test_crear_empleado_devuelve_201_con_id_y_queda_activo(gestion):
    id = crear(gestion)
    detalle = campos(gestion.get(f"{BASE}/empleados/{id}"))
    assert (detalle["nombre"], detalle["correo"], detalle["documento"], detalle["rol"], detalle["activo"]) == (
        "Elena Ruiz", "elena@chibchaweb.co", "E-2001", "Soporte", "true",
    )  # fmt: skip


def test_el_empleado_nuevo_entra_con_su_cuenta_externa_rn07(gestion):
    crear(gestion)
    nuevo = empleado_en_sesion("elena@chibchaweb.co")
    assert nuevo.get(f"{BASE}/auth/sesion").json()["rol"] == "Soporte"


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"nombre": "  "}, "nombre"),
        ({"correo": "no-es-correo"}, "correo"),
        ({"telefono": "abc"}, "telefono"),
        ({"documento": "con espacio"}, "documento"),
        ({"idRol": 999}, "idRol"),
    ],
)
def test_crear_empleado_con_datos_invalidos_es_422_con_campo(gestion, cambios, campo):
    assert_error(gestion.post(f"{BASE}/empleados", cuerpo(**cambios), format="json"), 422, "VALIDACION", campo)
    assert len(gestion.get(f"{BASE}/empleados").json()) == 3


def test_crear_empleado_con_cuerpo_incompleto_es_400(gestion):
    sin_rol = {k: v for k, v in NUEVO.items() if k != "idRol"}
    assert_error(gestion.post(f"{BASE}/empleados", sin_rol, format="json"), 400, "SOLICITUD_INVALIDA", "idRol")
    assert_error(
        gestion.post(f"{BASE}/empleados", cuerpo(idRol="x"), format="json"), 400, "SOLICITUD_INVALIDA", "idRol"
    )


def test_crear_empleado_con_correo_o_documento_repetido_es_409_duplicado(gestion):
    crear(gestion)
    assert_error(gestion.post(f"{BASE}/empleados", cuerpo(documento="E-9"), format="json"), 409, "DUPLICADO", "correo")
    assert_error(
        gestion.post(f"{BASE}/empleados", cuerpo(correo="otro@chibchaweb.co"), format="json"),
        409, "DUPLICADO", "documento",
    )  # fmt: skip
    assert_error(
        gestion.post(f"{BASE}/empleados", cuerpo(correo="soporte@chibchaweb.co", documento="E-9"), format="json"),
        409, "DUPLICADO", "correo",
    )  # fmt: skip


# --- EMP-03 --------------------------------------------------------------------------------------
def test_modificar_empleado_devuelve_204_y_cambia_los_datos(gestion):
    id = crear(gestion)
    r = gestion.put(
        f"{BASE}/empleados/{id}", cuerpo(nombre="Elena R.", idRol=1, correo="elena2@chibchaweb.co"), format="json"
    )
    assert r.status_code == 204 and not r.content
    detalle = campos(gestion.get(f"{BASE}/empleados/{id}"))
    assert (detalle["nombre"], detalle["rol"], detalle["correo"]) == ("Elena R.", "Gestión", "elena2@chibchaweb.co")


def test_modificar_empleado_sin_cambiar_correo_ni_documento_es_204(gestion):
    id = crear(gestion)
    assert gestion.put(f"{BASE}/empleados/{id}", cuerpo(telefono="3000000000"), format="json").status_code == 204


def test_modificar_empleado_con_datos_de_otro_es_409_y_con_datos_invalidos_422(gestion):
    id = crear(gestion)
    assert_error(
        gestion.put(f"{BASE}/empleados/{id}", cuerpo(correo="soporte@chibchaweb.co"), format="json"),
        409, "DUPLICADO", "correo",
    )  # fmt: skip
    assert_error(
        gestion.put(f"{BASE}/empleados/{id}", cuerpo(documento="E-1002"), format="json"), 409, "DUPLICADO", "documento"
    )
    assert_error(gestion.put(f"{BASE}/empleados/{id}", cuerpo(idRol=999), format="json"), 422, "VALIDACION", "idRol")
    assert_error(
        gestion.put(f"{BASE}/empleados/{id}", cuerpo(telefono="x"), format="json"), 422, "VALIDACION", "telefono"
    )


def test_modificar_empleado_inexistente_es_404_e_inactivo_es_409(gestion):
    assert_error(gestion.put(f"{BASE}/empleados/999999", cuerpo(), format="json"), 404, "NO_ENCONTRADO")
    id = crear(gestion)
    gestion.delete(f"{BASE}/empleados/{id}")
    assert_error(gestion.put(f"{BASE}/empleados/{id}", cuerpo(), format="json"), 409, "ESTADO_INVALIDO")


# --- EMP-04 --------------------------------------------------------------------------------------
def test_eliminar_empleado_es_baja_logica_204(gestion):
    id = crear(gestion)
    r = gestion.delete(f"{BASE}/empleados/{id}")
    assert r.status_code == 204 and not r.content
    assert campos(gestion.get(f"{BASE}/empleados/{id}"))["activo"] == "false"  # la fila sigue existiendo
    (fila,) = gestion.get(f"{BASE}/empleados", {"filtro": "E-2001"}).json()
    assert fila["estado"] == "INACTIVO"


def test_eliminar_empleado_ya_inactivo_es_idempotente_204(gestion):
    id = crear(gestion)
    assert gestion.delete(f"{BASE}/empleados/{id}").status_code == 204
    assert gestion.delete(f"{BASE}/empleados/{id}").status_code == 204


def test_eliminar_empleado_inexistente_o_de_otro_tipo_es_404(gestion, cliente_http):
    assert_error(gestion.delete(f"{BASE}/empleados/999999"), 404, "NO_ENCONTRADO")
    assert_error(gestion.delete(f"{BASE}/empleados/{cliente_http.id_usuario}"), 404, "NO_ENCONTRADO")


def test_un_empleado_dado_de_baja_no_puede_volver_a_entrar_403(gestion, anonimo):
    from tests.web.conftest import entrar

    id = crear(gestion)
    gestion.delete(f"{BASE}/empleados/{id}")
    assert_error(entrar(anonimo, "elena@chibchaweb.co"), 403, "USUARIO_INACTIVO")


def test_la_baja_cierra_las_sesiones_abiertas_del_empleado(gestion):
    id = crear(gestion)
    elena = empleado_en_sesion("elena@chibchaweb.co")
    assert elena.get(f"{BASE}/auth/sesion").status_code == 200
    assert gestion.delete(f"{BASE}/empleados/{id}").status_code == 204
    assert_error(elena.get(f"{BASE}/auth/sesion"), 403, "USUARIO_INACTIVO")
    assert_error(elena.get(f"{BASE}/auth/sesion"), 401, "NO_AUTENTICADO")  # la sesión se descartó
    assert gestion.get(f"{BASE}/empleados").status_code == 200  # las demás sesiones siguen sirviendo


def test_s3_el_cambio_de_cargo_se_aplica_a_la_sesion_abierta(gestion):
    """S-3: las operaciones no se toman de la cookie: se releen del empleado en cada petición."""
    id = crear(gestion, idRol=2)  # Soporte: ATENDER_TICKETS, sin GESTIONAR_EMPLEADOS
    elena = empleado_en_sesion("elena@chibchaweb.co")
    assert elena.get(f"{BASE}/tickets/diarios").status_code == 200
    assert_error(elena.get(f"{BASE}/empleados"), 403, "SIN_PERMISO")
    assert gestion.put(f"{BASE}/empleados/{id}", cuerpo(idRol=1), format="json").status_code == 204  # a Gestión
    assert_error(elena.get(f"{BASE}/tickets/diarios"), 403, "SIN_PERMISO")  # la operación anterior se perdió
    assert elena.get(f"{BASE}/empleados").status_code == 200  # y la nueva funciona
    sesion = elena.get(f"{BASE}/auth/sesion").json()
    assert sesion["rol"] == "Gestión" and "GESTIONAR_EMPLEADOS" in sesion["operaciones"]
    assert "ATENDER_TICKETS" not in sesion["operaciones"]
