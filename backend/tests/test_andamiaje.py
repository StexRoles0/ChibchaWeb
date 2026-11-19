"""Prueba de humo de la Fase 0."""

from django.conf import settings


def test_configuracion_basica():
    assert settings.USE_TZ is True
    assert settings.TIME_ZONE == "America/Bogota"
    assert settings.ROOT_URLCONF == "config.urls"


def test_contenedor_es_unico():
    from config.contenedor import contenedor

    assert contenedor() is contenedor()


def test_api_v1_montada():
    from chibchaweb.web import urls

    assert len(urls.urlpatterns) >= 12
