"""Comprueba que la BD de prueba se crea con el esquema y la semilla."""

import pytest


@pytest.mark.django_db
def test_esquema_y_semilla_aplicados():
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM rol_operacion")
        assert cursor.fetchone()[0] > 0
