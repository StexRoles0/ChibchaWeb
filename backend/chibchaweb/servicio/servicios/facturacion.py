"""Facturación (FAC): cobro automático de las suscripciones vencidas (CU-FAC-01)."""

from __future__ import annotations

import logging
from datetime import date

from chibchaweb.dominio.errores import ContingenciaActivaError, ErrorDominio
from chibchaweb.dominio.integraciones import PasarelaPago
from chibchaweb.dominio.repositorios import RepositorioSuscripcion

_registro = logging.getLogger(__name__)


class ServicioFacturacion:
    """Cobro automático periódico (módulo FAC). Lo dispara el programador de tareas."""

    def __init__(self, pasarela: PasarelaPago, suscripciones: RepositorioSuscripcion):
        self._pasarela = pasarela
        self._suscripciones = suscripciones

    def cargar_pago(self, fecha_corte: date) -> int:
        """CU-FAC-01 (RN-02, RN-03). Cobra las suscripciones activas vencidas a la fecha y devuelve cuántos cobros
        procesó (exitosos y fallidos).

        - El cobro lo hace ``Suscripcion.cobrar``: un pago EXITOSO avanza el corte; uno FALLIDO (rechazo, falla de
          la pasarela o tarjeta vencida) deja el corte donde estaba y **no** detiene el lote.
        - Si la BD cae (``ContingenciaActivaError``) el lote se **detiene**: el evento quedó respaldado y seguir
          cobrando dejaría suscripciones cobradas sin que la BD lo sepa. La tarea no vuelve a correr mientras haya
          eventos pendientes en el respaldo.
        - Un error del dominio en una sola suscripción se registra (solo su id) y el lote continúa con las demás.
        """
        procesados = 0
        for suscripcion in self._suscripciones.buscar_vencidas(fecha_corte):
            if not suscripcion.activa or not suscripcion.esta_vencida(fecha_corte):  # RN-02: se vuelve a comprobar
                continue
            try:
                pago = suscripcion.cobrar(self._pasarela)
                self._suscripciones.registrar_pago(pago)
                self._suscripciones.actualizar(suscripcion)
            except ContingenciaActivaError as exc:
                raise ContingenciaActivaError(
                    f"{exc.mensaje} El lote de cobros se detuvo tras {procesados} cobros procesados."
                ) from exc
            except ErrorDominio:
                _registro.exception("No se pudo cobrar la suscripción %s", suscripcion.id)
                continue
            procesados += 1
        return procesados
