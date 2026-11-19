"""CU-COM-02 (actor Tiempo): emite el cheque de cada comisión que no lo tiene. Cron el día 1 de cada mes (D-09)."""

from django.core.management.base import BaseCommand, CommandError

from chibchaweb.servicio.errores import ContingenciaActivaError, ErrorDominio
from chibchaweb.tareas._comun import ejecutar, exigir_sin_pendientes
from config.contenedor import contenedor


class Command(BaseCommand):
    help = "Genera el cheque de cada comisión sin cheque (P-08). CU-COM-02, RN-21."

    def handle(self, *args, **opciones):
        exigir_sin_pendientes()
        servicio = contenedor().servicio_comisiones
        pendientes = ejecutar(servicio.consultar_comisiones_sin_cheque)
        generados = 0
        errores = []
        for comision in pendientes:
            try:
                servicio.generar_cheque(comision.id)
            except ContingenciaActivaError as exc:  # la BD cayó: se detiene (el evento quedó respaldado)
                raise CommandError(f"Contingencia activa tras {generados} cheques generados: {exc.mensaje}") from exc
            except ErrorDominio as exc:  # una comisión con problema no frena las demás
                errores.append(f"comisión {comision.id}: {exc.mensaje}")
                self.stderr.write(f"No se generó el cheque de la comisión {comision.id}: {exc.mensaje}")
                continue
            generados += 1
        self.stdout.write(f"generar_cheques: {generados} cheques generados de {len(pendientes)} comisiones sin cheque")
        if errores:
            raise CommandError(f"{len(errores)} comisiones sin cheque por error: " + "; ".join(errores))
