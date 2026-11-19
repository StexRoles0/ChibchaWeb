"""Fixtures globales. La BD de prueba se crea con docs/schema.sql + docs/seed_dev.sql (D-03, D-14)."""

import os
from pathlib import Path

import pytest

# En el contenedor los docs se montan en /docs; en local están en ../docs
_DOCS = Path(os.environ.get("RUTA_DOCS", Path(__file__).resolve().parents[2] / "docs"))


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Tras crear la BD de prueba, aplica el esquema y la semilla de desarrollo."""
    from django.db import connection

    with django_db_blocker.unblock(), connection.cursor() as cursor:
        for nombre in ("schema.sql", "seed_dev.sql"):
            cursor.execute((_DOCS / nombre).read_text(encoding="utf-8"))
