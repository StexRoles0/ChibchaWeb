"""CU-CON-01 y CU-CON-02: ``/consultas/{tipoEntidad}`` (api.md §Consultas)."""

import pytest

from chibchaweb.dominio.soporte import CategoriaTicket, Ticket
from config.contenedor import contenedor
from tests.web.conftest import BASE, assert_error, cliente_en_sesion

CLAVES_CLIENTE = [
    "nombre", "correo", "telefono", "lineaResidencia", "ciudadResidencia", "codigoPostalResidencia",
    "lineaFacturacion", "ciudadFacturacion", "codigoPostalFacturacion", "tarjeta", "franquicia", "vencimiento",
    "idSuscripcion", "sitio", "plataforma", "idPaquete", "paquete", "idPlan", "plan", "montoPeriodo", "fechaCorte",
    "distribuidor", "activo",
]  # fmt: skip


@pytest.fixture
def ticket_id(cliente_http):
    c = contenedor()
    cliente = c.usuarios.buscar_por_id(cliente_http.id_usuario)
    t = Ticket("No carga el sitio", CategoriaTicket.RENDIMIENTO, cliente, c.catalogo.buscar_nivel_inicial(),
               sitio_afectado=cliente.suscripciones[0].sitio)  # fmt: skip
    return c.tickets.insertar(t)


def claves(respuesta):
    return [campo.partition(":")[0] for campo in respuesta.json()["campos"]]


# --- CON-01 --------------------------------------------------------------------------------------
def test_basico_de_clientes_para_gestion(gestion, cliente_http):
    r = gestion.get(f"{BASE}/consultas/CLIENTE", {"filtro": "LAURA"})  # sin distinguir mayúsculas
    assert r.status_code == 200
    (fila,) = r.json()
    assert fila == {
        "id": cliente_http.id_usuario,
        "titulo": "Laura",
        "subtitulo": "laura@correo.co · tiendalaura.chibchaweb.com · Chibcha-Oro",
        "estado": "ACTIVO",
    }
    assert gestion.get(f"{BASE}/consultas/CLIENTE", {"filtro": "zzz"}).json() == []


def test_basico_de_empleados_y_distribuidores(gestion):
    empleados = gestion.get(f"{BASE}/consultas/EMPLEADO").json()
    assert {e["titulo"] for e in empleados} == {"Gabriela Gestión", "Sergio Soporte", "Ana Administra"}
    assert [e["subtitulo"] for e in gestion.get(f"{BASE}/consultas/EMPLEADO", {"filtro": "E-1002"}).json()] == [
        "E-1002 · Soporte"
    ]
    (d,) = gestion.get(f"{BASE}/consultas/DISTRIBUIDOR").json()
    assert d["subtitulo"] == "900123456 · DIS-ANDES1 · 0 referidos" and d["estado"] == "ACTIVO"


def test_basico_de_tickets_para_soporte(soporte, ticket_id):
    (fila,) = soporte.get(f"{BASE}/consultas/TICKET", {"filtro": "no carga"}).json()
    assert fila == {"id": ticket_id, "titulo": "RENDIMIENTO", "subtitulo": "Soporte", "estado": "ABIERTO"}


def test_permisos_por_tipo_de_entidad(gestion, soporte, admin, cliente_http, anonimo):
    for tipo in ("CLIENTE", "EMPLEADO", "DISTRIBUIDOR"):
        assert gestion.get(f"{BASE}/consultas/{tipo}").status_code == 200
        assert_error(soporte.get(f"{BASE}/consultas/{tipo}"), 403, "SIN_PERMISO")
        assert_error(admin.get(f"{BASE}/consultas/{tipo}"), 403, "SIN_PERMISO")
    assert soporte.get(f"{BASE}/consultas/TICKET").status_code == 200
    assert_error(gestion.get(f"{BASE}/consultas/TICKET"), 403, "SIN_PERMISO")
    for tipo in ("CLIENTE", "TICKET"):
        assert_error(cliente_http.get(f"{BASE}/consultas/{tipo}"), 403, "SIN_PERMISO")
        assert_error(anonimo.get(f"{BASE}/consultas/{tipo}"), 401, "NO_AUTENTICADO")


def test_tipo_de_entidad_desconocido_es_400(gestion):
    assert_error(gestion.get(f"{BASE}/consultas/PROVEEDOR"), 400, "SOLICITUD_INVALIDA", "tipo")
    assert_error(gestion.get(f"{BASE}/consultas/cliente"), 400, "SOLICITUD_INVALIDA", "tipo")  # exacto, en mayúsculas


# --- CON-02 --------------------------------------------------------------------------------------
def test_detalle_de_cliente_para_gestion(gestion, cliente_http):
    r = gestion.get(f"{BASE}/consultas/CLIENTE/{cliente_http.id_usuario}")
    assert r.status_code == 200 and claves(r) == CLAVES_CLIENTE and r.json()["titulo"] == "Laura"
    assert "tarjeta: VISA •••• 4242" in r.json()["campos"] and "4242424242424242" not in r.content.decode()


def test_detalle_de_empleado_y_distribuidor(gestion, soporte):
    (empleado,) = gestion.get(f"{BASE}/consultas/EMPLEADO", {"filtro": "soporte@"}).json()
    r = gestion.get(f"{BASE}/consultas/EMPLEADO/{empleado['id']}")
    assert claves(r) == ["nombre", "documento", "correo", "telefono", "idRol", "rol", "activo", "fechaRegistro"]
    assert "rol: Soporte" in r.json()["campos"] and "activo: true" in r.json()["campos"]
    (dist,) = gestion.get(f"{BASE}/consultas/DISTRIBUIDOR").json()
    r = gestion.get(f"{BASE}/consultas/DISTRIBUIDOR/{dist['id']}")
    assert claves(r) == ["nombre", "documento", "correo", "telefono", "codigo", "categoria", "referidos", "activo"]
    assert "codigo: DIS-ANDES1" in r.json()["campos"] and "categoria: Básico" in r.json()["campos"]


def test_detalle_de_ticket_para_soporte(soporte, ticket_id):
    r = soporte.get(f"{BASE}/consultas/TICKET/{ticket_id}")
    assert r.status_code == 200 and r.json()["titulo"] == f"Ticket #{ticket_id}"
    assert claves(r) == ["categoria", "estado", "nivel", "reportante", "sitio", "fechaCreacion", "descripcion"]
    assert "sitio: tiendalaura.chibchaweb.com" in r.json()["campos"] and "estado: ABIERTO" in r.json()["campos"]


def test_detalle_inexistente_es_404(gestion, soporte):
    assert_error(gestion.get(f"{BASE}/consultas/CLIENTE/999999"), 404, "NO_ENCONTRADO")
    assert_error(soporte.get(f"{BASE}/consultas/TICKET/999999"), 404, "NO_ENCONTRADO")


def test_detalle_de_otro_tipo_de_usuario_es_404(gestion, cliente_http):
    assert_error(gestion.get(f"{BASE}/consultas/EMPLEADO/{cliente_http.id_usuario}"), 404, "NO_ENCONTRADO")


def test_detalle_con_tipo_desconocido_o_id_no_numerico(gestion):
    assert_error(gestion.get(f"{BASE}/consultas/XX/1"), 400, "SOLICITUD_INVALIDA", "tipo")
    assert gestion.get(f"{BASE}/consultas/CLIENTE/abc").status_code == 404


def test_detalle_sin_permiso(soporte, cliente_http, ticket_id, anonimo):
    assert_error(soporte.get(f"{BASE}/consultas/CLIENTE/{cliente_http.id_usuario}"), 403, "SIN_PERMISO")
    otro = cliente_en_sesion("otro@correo.co", sitio="otrositio")
    assert_error(otro.get(f"{BASE}/consultas/TICKET/{ticket_id}"), 403, "SIN_PERMISO")
    assert_error(anonimo.get(f"{BASE}/consultas/CLIENTE/1"), 401, "NO_AUTENTICADO")
