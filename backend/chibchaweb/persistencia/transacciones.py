"""Unidad de trabajo sobre transacciones de Django (P-04, RN-27)."""

from __future__ import annotations

from django.db import transaction

from chibchaweb import transaccion as cuenta_de_escrituras
from chibchaweb.dominio.errores import EstadoInvalidoError
from chibchaweb.dominio.repositorios import UnidadDeTrabajo


class UnidadDeTrabajoDjango(UnidadDeTrabajo):
    """``transaction.atomic`` con savepoint: se puede usar dentro de la transacción de la petición.

    ``iniciar`` abre el bloque atómico (o un savepoint si ya hay transacción); ``confirmar`` lo cierra
    dejando los cambios y ``revertir`` lo cierra descartándolos. Admite unidades anidadas.
    """

    def __init__(self):
        self._bloques: list[transaction.Atomic] = []

    def iniciar(self) -> None:
        bloque = transaction.atomic()
        cuenta_de_escrituras.abrir()  # D-33: la unidad más externa pone en cero la cuenta de escrituras
        try:
            bloque.__enter__()
        except BaseException:
            cuenta_de_escrituras.cerrar()
            raise
        self._bloques.append(bloque)

    def confirmar(self) -> None:
        self._cerrar(revertir=False)

    def revertir(self) -> None:
        self._cerrar(revertir=True)

    def _cerrar(self, revertir: bool) -> None:
        if not self._bloques:
            raise EstadoInvalidoError("No hay una unidad de trabajo iniciada")
        bloque = self._bloques.pop()
        try:
            if revertir:
                transaction.set_rollback(True)
            bloque.__exit__(None, None, None)
        finally:
            cuenta_de_escrituras.cerrar()
