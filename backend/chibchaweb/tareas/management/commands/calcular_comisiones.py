"""CU-COM-01 (actor Tiempo): liquida las comisiones del periodo. Cron el día 1 de cada mes a las 03:00 (D-09)."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from chibchaweb.tareas._comun import ejecutar, exigir_sin_pendientes, fecha_iso
from config.contenedor import contenedor


class Command(BaseCommand):
    help = "Calcula las comisiones de los distribuidores en [inicio, fin] (por defecto, el mes anterior). CU-COM-01."

    def add_arguments(self, parser):
        parser.add_argument("--inicio", type=fecha_iso, help="Primer día del periodo AAAA-MM-DD")
        parser.add_argument("--fin", type=fecha_iso, help="Último día del periodo AAAA-MM-DD")

    def handle(self, *args, inicio=None, fin=None, **opciones):
        if (inicio is None) != (fin is None):
            raise CommandError("Indique --inicio y --fin juntos, o ninguno para usar el mes anterior")
        if inicio is None:
            fin = timezone.localdate().replace(day=1) - timedelta(days=1)  # último día del mes anterior
            inicio = fin.replace(day=1)
        exigir_sin_pendientes()
        creadas = ejecutar(lambda: contenedor().servicio_comisiones.calcular_comision(inicio, fin))
        self.stdout.write(f"calcular_comisiones {inicio.isoformat()} a {fin.isoformat()}: {creadas} comisiones creadas")
