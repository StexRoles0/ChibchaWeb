"""CU-FAC-01 (actor Tiempo): cobra las suscripciones vencidas. Cron diario a las 02:00 (D-09)."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from chibchaweb.tareas._comun import ejecutar, exigir_sin_pendientes, fecha_iso
from config.contenedor import contenedor


class Command(BaseCommand):
    help = "Cobra las suscripciones activas vencidas a la fecha (por defecto, hoy). CU-FAC-01, RN-02 y RN-03."

    def add_arguments(self, parser):
        parser.add_argument("--fecha", type=fecha_iso, help="Fecha de corte AAAA-MM-DD (por defecto, hoy)")

    def handle(self, *args, fecha=None, **opciones):
        fecha = fecha or timezone.localdate()
        exigir_sin_pendientes()
        procesados = ejecutar(lambda: contenedor().servicio_facturacion.cargar_pago(fecha))
        self.stdout.write(f"cargar_pagos {fecha.isoformat()}: {procesados} cobros procesados")
