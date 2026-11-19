"""Cuenta de escrituras por transacción (D-33). Módulo neutro: lo usan la web y la persistencia, y solo importa Django.

RT04 respalda la escritura que falló, no las anteriores de la misma transacción. Si una transacción ya había escrito
otras filas, el rollback las descarta y un evento respaldado quedaría huérfano (su sincronización fallaría siempre y,
como es todo o nada, bloquearía el respaldo). Por eso la persistencia no respalda cuando
``hay_escrituras_previas()``: responde 503 sin evento, el rollback deja la BD coherente y el usuario reintenta.

La transacción más externa la abren ``@transaccional`` (web) y ``UnidadDeTrabajoDjango`` (persistencia) con
``abrir()``/``cerrar()``. Fuera de ellas (tareas programadas, pruebas de un mapeador) cada escritura es su propia
transacción y nunca tiene escrituras previas.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from django.db import transaction


class _Estado(threading.local):
    profundidad = 0  # transacciones abiertas con abrir() (la más externa pone la cuenta en cero)
    escrituras = 0  # escrituras respaldables confirmadas dentro de la transacción más externa


_estado = _Estado()


def abrir() -> None:
    if _estado.profundidad == 0:
        _estado.escrituras = 0
    _estado.profundidad += 1


def cerrar() -> None:
    _estado.profundidad = max(0, _estado.profundidad - 1)
    if _estado.profundidad == 0:
        _estado.escrituras = 0


def registrar_escritura() -> None:
    """Una escritura respaldable terminó bien. Un savepoint revertido no la descuenta (criterio conservador)."""
    if _estado.profundidad > 0:
        _estado.escrituras += 1


def hay_escrituras_previas() -> bool:
    return _estado.profundidad > 0 and _estado.escrituras > 0


@contextmanager
def transaccion() -> Iterator[None]:
    """``transaction.atomic()`` que lleva la cuenta de escrituras de la transacción más externa."""
    abrir()
    try:
        with transaction.atomic():
            yield
    finally:
        cerrar()
