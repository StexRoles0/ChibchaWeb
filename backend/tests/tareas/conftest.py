"""Fixtures de los management commands (D-09): ``call_command`` contra PostgreSQL con adaptadores simulados."""

import pytest
from freezegun import freeze_time

from config.contenedor import contenedor

HOY = "2026-12-01 10:00:00-05:00"


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/tareas" in str(item.fspath):
            item.add_marker(pytest.mark.django_db)


@pytest.fixture(autouse=True)
def _contenedor_limpio(settings, tmp_path):
    settings.SIMULAR_EXTERNOS = True
    settings.RUTA_RESPALDO = str(tmp_path / "respaldo.log")
    contenedor.cache_clear()
    yield
    contenedor.cache_clear()


@pytest.fixture(autouse=True)
def _hoy_fijo():
    """Los registros nacen con corte = hoy (RN-04): todo el módulo corre el 1 de diciembre de 2026."""
    with freeze_time(HOY):
        yield
