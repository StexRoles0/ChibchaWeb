"""Fixtures de la API: ``APIClient`` contra PostgreSQL con adaptadores simulados (SIMULAR_EXTERNOS=true)."""

from urllib.parse import parse_qs, urlparse

import pytest
from rest_framework.test import APIClient

from config.contenedor import contenedor

BASE = "/api/v1"


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/web" in str(item.fspath):
            item.add_marker(pytest.mark.django_db)


@pytest.fixture(autouse=True)
def _contenedor_limpio(settings, tmp_path):
    settings.SIMULAR_EXTERNOS = True
    settings.RUTA_RESPALDO = str(tmp_path / "respaldo.log")
    contenedor.cache_clear()
    yield
    contenedor.cache_clear()


@pytest.fixture
def anonimo():
    return APIClient()


def entrar(cliente: APIClient, correo: str, prefijo: str = "dev"):
    """Flujo de AUTH-01 y AUTH-02 con el proveedor simulado: pide la URL, toma el ``state`` y manda el código."""
    inicio = cliente.get(f"{BASE}/auth/oauth/inicio", {"correo": correo})
    assert inicio.status_code == 200, inicio.content
    consulta = parse_qs(urlparse(inicio.json()["url"]).query)
    return cliente.post(
        f"{BASE}/auth/oauth/callback",
        {"codigo": f"{prefijo}:{correo}", "estado": consulta["state"][0]},
        format="json",
    )


def cuerpo_registro(**cambios):
    cuerpo = {
        "telefono": "3001234567",
        "lineaResidencia": "Calle 10 # 5-20",
        "ciudadResidencia": "Bogotá",
        "codigoPostalResidencia": "110111",
        "sitio": "tiendalaura",
        "plataforma": "UNIX",
        "idPaquete": 2,
        "idPlan": 3,
        "lineaFacturacion": "Carrera 7 # 40-10",
        "ciudadFacturacion": "Bogotá",
        "codigoPostalFacturacion": "110231",
        "numeroTarjeta": "4242424242424242",
        "vencimiento": "2099-12-01",
        "codigoSeguridad": "123",
        "franquicia": "VISA",
    }
    cuerpo.update(cambios)
    return {k: v for k, v in cuerpo.items() if v is not None}


def cliente_en_sesion(correo="laura@correo.co", **cambios) -> APIClient:
    """Visitante nuevo que completa el registro y queda con la sesión abierta."""
    http = APIClient()
    assert entrar(http, correo).json()["registrado"] is False
    respuesta = http.post(f"{BASE}/auth/registro", cuerpo_registro(**cambios), format="json")
    assert respuesta.status_code == 201, respuesta.content
    http.id_usuario = respuesta.json()["idUsuario"]
    return http


def empleado_en_sesion(correo: str) -> APIClient:
    http = APIClient()
    respuesta = entrar(http, correo)
    assert respuesta.status_code == 200 and respuesta.json()["registrado"] is True, respuesta.content
    return http


@pytest.fixture
def cliente_http():
    return cliente_en_sesion()


@pytest.fixture
def gestion():
    return empleado_en_sesion("gestion@chibchaweb.co")


@pytest.fixture
def soporte():
    return empleado_en_sesion("soporte@chibchaweb.co")


@pytest.fixture
def admin():
    return empleado_en_sesion("admin@chibchaweb.co")


def assert_error(respuesta, estado: int, codigo: str, campo: str | None = None):
    cuerpo = respuesta.json()
    assert respuesta.status_code == estado, cuerpo
    assert cuerpo["codigo"] == codigo and cuerpo["mensaje"], cuerpo
    assert cuerpo.get("campo") == campo, cuerpo
