"""B1: la configuración falla al arrancar si es insegura para producción."""

import runpy
from pathlib import Path

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured

RUTA = Path(__file__).resolve().parents[1] / "config" / "settings.py"
CLAVE_DEV = "ZGV2LWNsYXZlLWNpZnJhZG8tMzItYnl0ZXMtMDAwMDA="
CLAVE_PROPIA = "cHJvcGlhLWNsYXZlLWRlLTMyLWJ5dGVzLXByb2R1Y2M="


PROD_OIDC = {
    "DJANGO_DEBUG": "False",
    "CLAVE_CIFRADO": CLAVE_PROPIA,
    "DJANGO_SECRET_KEY": "una-clave-secreta-larga-y-propia",
    "SIMULAR_EXTERNOS": "false",
    "OIDC_CLIENT_SECRET": "s",
    "OIDC_REDIRECT_URI": "https://x/cb",
}


def cargar(monkeypatch, **entorno):
    # Aislado del .env del desarrollador: solo cuenta lo que la prueba define.
    monkeypatch.setattr(environ.Env, "read_env", classmethod(lambda cls, *a, **k: None))
    for clave, valor in entorno.items():
        monkeypatch.setenv(clave, valor)
    return runpy.run_path(str(RUTA))


@pytest.mark.parametrize("clave", ["", CLAVE_DEV])
def test_sin_debug_la_clave_de_cifrado_de_desarrollo_o_vacia_se_rechaza(monkeypatch, clave):
    with pytest.raises(ImproperlyConfigured, match="CLAVE_CIFRADO"):
        cargar(monkeypatch, **{**PROD_OIDC, "CLAVE_CIFRADO": clave})


def test_sin_debug_con_clave_propia_arranca(monkeypatch):
    ajustes = cargar(monkeypatch, **PROD_OIDC)
    assert ajustes["CLAVE_CIFRADO"] == CLAVE_PROPIA


def test_con_debug_la_clave_de_desarrollo_es_valida(monkeypatch):
    assert cargar(monkeypatch, DJANGO_DEBUG="True", CLAVE_CIFRADO=CLAVE_DEV)["DEBUG"] is True


@pytest.mark.parametrize("faltante", ["OIDC_CLIENT_SECRET", "OIDC_REDIRECT_URI"])
def test_externos_reales_exigen_secreto_y_uri(monkeypatch, faltante):
    entorno = {"SIMULAR_EXTERNOS": "false", "OIDC_CLIENT_SECRET": "s", "OIDC_REDIRECT_URI": "http://x/cb"}
    entorno[faltante] = ""
    with pytest.raises(ImproperlyConfigured, match="OIDC"):
        cargar(monkeypatch, **entorno)


# --- Revisión final: S-1, S-2 y S-4 ---------------------------------------------------------------
PROD = {"DJANGO_DEBUG": "False", "CLAVE_CIFRADO": CLAVE_PROPIA, "DJANGO_SECRET_KEY": "una-clave-secreta-larga-y-propia"}
CLAVE_DJANGO_DEV = "clave-solo-para-desarrollo-no-usar-en-produccion"


@pytest.mark.parametrize("valor", ["", CLAVE_DJANGO_DEV])
def test_sin_debug_la_secret_key_vacia_o_de_desarrollo_se_rechaza(monkeypatch, valor):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        cargar(monkeypatch, **{**PROD, "DJANGO_SECRET_KEY": valor, "SIMULAR_EXTERNOS": "false"})


def test_sin_debug_y_sin_secret_key_en_el_entorno_se_rechaza(monkeypatch):
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    entorno = {k: v for k, v in PROD.items() if k != "DJANGO_SECRET_KEY"}
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        cargar(monkeypatch, **entorno)


def test_sin_debug_no_se_permiten_los_externos_simulados(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="SIMULAR_EXTERNOS"):
        cargar(monkeypatch, **PROD, SIMULAR_EXTERNOS="true")


def test_sin_debug_los_externos_son_reales_por_defecto(monkeypatch):
    monkeypatch.delenv("SIMULAR_EXTERNOS", raising=False)
    with pytest.raises(ImproperlyConfigured, match="OIDC"):  # reales por defecto: exigen secreto y URI
        cargar(monkeypatch, **{**PROD, "OIDC_CLIENT_SECRET": "", "OIDC_REDIRECT_URI": ""})


def test_sin_debug_con_todo_propio_arranca_con_cookies_seguras(monkeypatch):
    ajustes = cargar(
        monkeypatch, **PROD, SIMULAR_EXTERNOS="false", OIDC_CLIENT_SECRET="s", OIDC_REDIRECT_URI="https://x/cb"
    )
    assert ajustes["SESSION_COOKIE_SECURE"] is True
    assert ajustes["CSRF_COOKIE_SECURE"] is True
    assert ajustes["SIMULAR_EXTERNOS"] is False


def test_con_debug_los_valores_por_defecto_son_de_desarrollo(monkeypatch):
    monkeypatch.delenv("SIMULAR_EXTERNOS", raising=False)
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    ajustes = cargar(monkeypatch, DJANGO_DEBUG="True")
    assert ajustes["SIMULAR_EXTERNOS"] is True
    assert ajustes["SECRET_KEY"] == CLAVE_DJANGO_DEV
    assert ajustes["SESSION_COOKIE_SECURE"] is False
    assert ajustes["CSRF_COOKIE_SECURE"] is False
