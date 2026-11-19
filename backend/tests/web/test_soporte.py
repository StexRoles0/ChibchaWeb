"""CU-SOP-01..03: ``/tickets`` (api.md §Soporte)."""

from datetime import date

import pytest

from tests.web.conftest import BASE, assert_error, cliente_en_sesion

TICKET = {"categoria": "RENDIMIENTO", "descripcion": "El sitio no carga"}


def registrar(http, **cambios):
    r = http.post(f"{BASE}/tickets", {**TICKET, **cambios}, format="json")
    assert r.status_code == 201, r.content
    return r.json()["id"]


def campos(r) -> dict[str, list[str]]:
    salida: dict[str, list[str]] = {}
    for c in r.json()["campos"]:
        clave, _, valor = c.partition(": ")
        salida.setdefault(clave, []).append(valor)
    return salida


def enrutar(http, id, escalar, observacion="Revisado"):
    cuerpo = {"escalar": escalar} if observacion is None else {"escalar": escalar, "observacion": observacion}
    return http.post(f"{BASE}/tickets/{id}/enrutamiento", cuerpo, format="json")


# --- SOP-01 (RN-22) ------------------------------------------------------------------------------
def test_cliente_registra_ticket_con_sitio_201(cliente_http, soporte):
    (sitio,) = cliente_http.get(f"{BASE}/clientes/me/sitios").json()
    id = registrar(cliente_http, categoria="CORREO", idSitio=sitio["id"])
    d = campos(soporte.get(f"{BASE}/tickets/{id}"))
    assert d["estado"] == ["ABIERTO"] and d["nivel"] == ["Soporte"] and d["categoria"] == ["CORREO"]
    assert d["sitio"] == ["tiendalaura.chibchaweb.com"] and d["reportante"] == ["Laura (cliente)"]
    assert "movimiento" not in d


def test_ticket_sin_sitio_y_con_categoria_legible_del_frontend(cliente_http, soporte):
    id = registrar(cliente_http, categoria="Base de datos", idSitio=None)
    d = campos(soporte.get(f"{BASE}/tickets/{id}"))
    assert d["categoria"] == ["BASE_DATOS"] and d["sitio"] == [""]


@pytest.mark.parametrize("categoria", ["Rendimiento", "Correo", "Base de datos", "Dominio", "Otra"])
def test_las_categorias_del_frontend_se_aceptan(cliente_http, categoria):
    registrar(cliente_http, categoria=categoria)


def test_cualquier_empleado_registra_ticket_rn22(gestion, soporte, admin):
    for http in (gestion, soporte, admin):
        registrar(http, descripcion="Mi equipo falla")


def test_un_empleado_no_puede_indicar_sitio_422(gestion, cliente_http):
    (sitio,) = cliente_http.get(f"{BASE}/clientes/me/sitios").json()
    assert_error(
        gestion.post(f"{BASE}/tickets", {**TICKET, "idSitio": sitio["id"]}, format="json"), 422, "VALIDACION", "idSitio"
    )


def test_el_sitio_debe_ser_del_cliente_422_regla_de_negocio(cliente_http):
    otro = cliente_en_sesion("otro@correo.co", sitio="otrositio")
    (ajeno,) = otro.get(f"{BASE}/clientes/me/sitios").json()
    assert_error(
        cliente_http.post(f"{BASE}/tickets", {**TICKET, "idSitio": ajeno["id"]}, format="json"), 422, "REGLA_NEGOCIO"
    )
    assert_error(
        cliente_http.post(f"{BASE}/tickets", {**TICKET, "idSitio": 999999}, format="json"), 422, "VALIDACION", "idSitio"
    )


def test_ticket_con_datos_invalidos(cliente_http):
    assert_error(
        cliente_http.post(f"{BASE}/tickets", {**TICKET, "descripcion": "  "}, format="json"),
        422,
        "VALIDACION",
        "descripcion",
    )
    assert_error(
        cliente_http.post(f"{BASE}/tickets", {**TICKET, "categoria": "OTRA COSA"}, format="json"),
        400, "SOLICITUD_INVALIDA", "categoria",
    )  # fmt: skip
    assert_error(
        cliente_http.post(f"{BASE}/tickets", {"categoria": "OTRA"}, format="json"),
        400,
        "SOLICITUD_INVALIDA",
        "descripcion",
    )
    assert_error(
        cliente_http.post(f"{BASE}/tickets", {**TICKET, "idSitio": "x"}, format="json"),
        400,
        "SOLICITUD_INVALIDA",
        "idSitio",
    )


def test_registrar_ticket_sin_sesion_401(anonimo):
    assert_error(anonimo.post(f"{BASE}/tickets", TICKET, format="json"), 401, "NO_AUTENTICADO")


def test_mis_tickets_solo_los_propios_recientes_primero(cliente_http, gestion):
    primero = registrar(cliente_http, categoria="CORREO")
    segundo = registrar(cliente_http, categoria="DOMINIO")
    registrar(gestion)
    filas = cliente_http.get(f"{BASE}/tickets/mios").json()
    assert filas == [
        {"id": segundo, "titulo": "DOMINIO", "subtitulo": "Soporte", "estado": "ABIERTO"},
        {"id": primero, "titulo": "CORREO", "subtitulo": "Soporte", "estado": "ABIERTO"},
    ]
    assert len(gestion.get(f"{BASE}/tickets/mios").json()) == 1


def test_mis_tickets_sin_sesion_401_y_vacio_si_no_hay(anonimo, cliente_http):
    assert_error(anonimo.get(f"{BASE}/tickets/mios"), 401, "NO_AUTENTICADO")
    assert cliente_http.get(f"{BASE}/tickets/mios").json() == []


# --- SOP-02 (RN-24) ------------------------------------------------------------------------------
def test_rn24_bandeja_de_hoy_por_defecto_con_los_abiertos(cliente_http, soporte):
    id = registrar(cliente_http)
    resuelto = registrar(cliente_http, categoria="OTRA")
    assert enrutar(soporte, resuelto, False).status_code == 204
    hoy = date.today().isoformat()
    for consulta in ({}, {"fecha": hoy}):
        filas = soporte.get(f"{BASE}/tickets/diarios", consulta).json()
        assert [f["id"] for f in filas] == [resuelto, id]  # creados hoy, del más reciente al más antiguo
    assert filas[1] == {"id": id, "titulo": "RENDIMIENTO", "subtitulo": "Soporte", "estado": "ABIERTO"}


def test_rn24_otro_dia_solo_muestra_los_abiertos(cliente_http, soporte):
    abierto = registrar(cliente_http)
    resuelto = registrar(cliente_http)
    enrutar(soporte, resuelto, False)
    assert [f["id"] for f in soporte.get(f"{BASE}/tickets/diarios", {"fecha": "2001-01-01"}).json()] == [abierto]


def test_bandeja_con_fecha_invalida_es_400(soporte):
    assert_error(soporte.get(f"{BASE}/tickets/diarios", {"fecha": "ayer"}), 400, "SOLICITUD_INVALIDA", "fecha")


def test_solo_soporte_ve_la_bandeja_y_el_detalle(cliente_http, gestion, admin, anonimo, soporte):
    id = registrar(cliente_http)
    for ruta in (f"{BASE}/tickets/diarios", f"{BASE}/tickets/{id}"):
        for http in (cliente_http, gestion, admin):
            assert_error(http.get(ruta), 403, "SIN_PERMISO")
        assert_error(anonimo.get(ruta), 401, "NO_AUTENTICADO")
        assert soporte.get(ruta).status_code == 200


def test_detalle_de_ticket_inexistente_404(soporte):
    assert_error(soporte.get(f"{BASE}/tickets/999999"), 404, "NO_ENCONTRADO")


# --- SOP-03 (RN-23) ------------------------------------------------------------------------------
def test_rn23_escalar_204_y_queda_trazabilidad(cliente_http, soporte):
    id = registrar(cliente_http)
    r = enrutar(soporte, id, True, "Pasa a gestión")
    assert r.status_code == 204 and not r.content
    d = campos(soporte.get(f"{BASE}/tickets/{id}"))
    assert d["estado"] == ["ESCALADO"] and d["nivel"] == ["Gestión"]
    (movimiento,) = d["movimiento"]
    fecha, responsable, estado, nivel, observacion = movimiento.split("|")
    assert (responsable, estado, nivel, observacion) == ("Sergio Soporte", "ESCALADO", "Gestión", "Pasa a gestión")
    assert len(fecha) == 16


def test_rn23_resolver_204(cliente_http, soporte):
    id = registrar(cliente_http)
    assert enrutar(soporte, id, False, "Resuelto").status_code == 204
    d = campos(soporte.get(f"{BASE}/tickets/{id}"))
    assert d["estado"] == ["RESUELTO"] and d["nivel"] == ["Soporte"]


def test_rn23_en_el_ultimo_nivel_escalar_es_409(cliente_http, soporte):
    id = registrar(cliente_http)
    assert enrutar(soporte, id, True, "uno").status_code == 204
    assert enrutar(soporte, id, True, "dos").status_code == 204
    assert campos(soporte.get(f"{BASE}/tickets/{id}"))["nivel"] == ["Desarrollo"]
    assert_error(enrutar(soporte, id, True, "tres"), 409, "ESTADO_INVALIDO")
    assert len(campos(soporte.get(f"{BASE}/tickets/{id}"))["movimiento"]) == 2


@pytest.mark.parametrize("escalar", [True, False])
def test_rn23_un_ticket_resuelto_es_409(cliente_http, soporte, escalar):
    id = registrar(cliente_http)
    enrutar(soporte, id, False, "listo")
    assert_error(enrutar(soporte, id, escalar, "otra vez"), 409, "ESTADO_INVALIDO")


@pytest.mark.parametrize("observacion", [None, "", "   "])
def test_rn23_sin_observacion_es_422(cliente_http, soporte, observacion):
    id = registrar(cliente_http)
    assert_error(enrutar(soporte, id, True, observacion), 422, "VALIDACION", "observacion")
    d = campos(soporte.get(f"{BASE}/tickets/{id}"))
    assert d["estado"] == ["ABIERTO"] and "movimiento" not in d


def test_rn23_cuerpo_invalido_es_400(cliente_http, soporte):
    id = registrar(cliente_http)
    r = soporte.post(f"{BASE}/tickets/{id}/enrutamiento", {"observacion": "x"}, format="json")
    assert_error(r, 400, "SOLICITUD_INVALIDA", "escalar")


def test_rn23_ticket_inexistente_es_404(soporte):
    assert_error(enrutar(soporte, 999999, True), 404, "NO_ENCONTRADO")


def test_rn23_solo_soporte_enruta(cliente_http, gestion, admin, anonimo):
    id = registrar(cliente_http)
    for http in (cliente_http, gestion, admin):
        assert_error(enrutar(http, id, True), 403, "SIN_PERMISO")
    assert_error(enrutar(anonimo, id, True), 401, "NO_AUTENTICADO")
