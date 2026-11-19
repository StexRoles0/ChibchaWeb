# Se ejecuta dentro del contenedor backend: `manage.py shell < evento_respaldado.py`.
# Deja en el archivo de respaldo un evento SolicitudDominio.insertar REAL: simula que la BD cae justo al escribir
# (el ORM falla en `save`) y el mapeador respalda el evento cifrado con el algoritmo indicado (mismo camino que
# usa la API). No toca la BD de negocio.
import os
from unittest import mock

from django.db import OperationalError
from django.db.models import Model
from django.db.models.query import QuerySet

from config.contenedor import contenedor

servicio = contenedor().servicio_contingencia
servicio.cambiar_algoritmo_cifrado(os.environ["E2E_ALGORITMO"])
try:
    with (
        mock.patch.object(Model, "save", side_effect=OperationalError("sin BD")),
        mock.patch.object(QuerySet, "update", side_effect=OperationalError("sin BD")),
    ):
        contenedor().servicio_dominios.registrar_solicitud_dominio(
            int(os.environ["E2E_CLIENTE"]), os.environ["E2E_NOMBRE"], ".com"
        )
except Exception as exc:  # ContingenciaActivaError: el evento quedó respaldado
    print("RESPALDADO", type(exc).__name__)
