"""Layer Supertype ``Mapeador<T>`` y auxiliares comunes de los mapeadores (solo traducen, sin reglas de negocio)."""

from __future__ import annotations

import functools
import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Generic, TypeVar

from django.db import DataError, IntegrityError, InterfaceError, OperationalError, connection, transaction

from chibchaweb.dominio.errores import (
    ContingenciaActivaError,
    DuplicadoError,
    NoEncontradoError,
    ReglaNegocioError,
)
from chibchaweb.dominio.respaldo import GestorContingencia
from chibchaweb.persistencia.modelos_orm import ZONA
from chibchaweb.transaccion import hay_escrituras_previas, registrar_escritura

T = TypeVar("T")

# Nombre de la restricción UNIQUE de PostgreSQL -> campo del dominio que se duplicó.
_CAMPOS_UNICOS = {
    "usuario_correo_key": "correo",
    "empleado_documento_key": "documento",
    "distribuidor_documento_key": "documento",
    "distribuidor_codigo_key": "codigo",
    "cuenta_acceso_proveedor_identificador_externo_key": "identificadorExterno",
    "cuenta_acceso_id_titular_key": "cuenta",
    "sitio_web_subdominio_key": "sitio",
    "sitio_web_dominio_propio_key": "dominioPropio",
    "cheque_numero_key": "numero",
    "cheque_id_comision_key": "cheque",
}


def traducir_fallas_de_lectura[C: type](clase: C) -> C:
    """Decorador de clase: toda lectura (``buscar_*``, ``listar_*``, ``existe``) que falle por la BD lanza
    ``ContingenciaActivaError`` (503) en vez de un 500. Las lecturas no se respaldan (RT04)."""

    def envolver(funcion):
        @functools.wraps(funcion)
        def lectura(*args, **kwargs):
            try:
                return funcion(*args, **kwargs)
            except (OperationalError, InterfaceError) as exc:
                raise ContingenciaActivaError(
                    "La base de datos no está disponible; la consulta no se pudo realizar"
                ) from exc

        return lectura

    for nombre, valor in list(vars(clase).items()):
        if callable(valor) and nombre.startswith(("buscar_", "listar_", "existe")):
            setattr(clase, nombre, envolver(valor))
    return clase


@traducir_fallas_de_lectura
class Mapeador(ABC, Generic[T]):  # noqa: UP046 - el modelo la define como Generic, ABC
    """Operaciones comunes de los mapeadores de datos (Data Mapper con Layer Supertype)."""

    def __init__(self, nombre_tabla: str):
        self._nombre_tabla = nombre_tabla  # «#nombreTabla»: tabla principal que mapea la subclase

    @property
    def nombre_tabla(self) -> str:
        return self._nombre_tabla

    @abstractmethod
    def insertar(self, objeto: T) -> int:
        """Inserta el objeto y devuelve su id."""

    @abstractmethod
    def actualizar(self, objeto: T) -> None:
        """Actualiza el objeto."""

    @abstractmethod
    def buscar_por_id(self, id: int) -> T:
        """Reconstruye el objeto por su id."""

    @abstractmethod
    def buscar_por_filtro(self, filtro: str) -> list[T]:
        """Devuelve los objetos que coinciden con el filtro."""

    def existe(self, id: int) -> bool:
        """Indica si existe un registro con el id en ``nombre_tabla``."""
        tabla = connection.ops.quote_name(self._nombre_tabla)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT 1 FROM {tabla} WHERE id = %s", [id])  # noqa: S608 - tabla fija de la subclase
            return cursor.fetchone() is not None


# --------------------------------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------------------------------


def con_contingencia[R](
    gestor: GestorContingencia, tipo_evento: str, contenido: Callable[[], str], accion: Callable[[], R]
) -> R:
    """Ejecuta la escritura en una transacción; si la BD falla (RT04) respalda el evento y avisa.

    ``tipo_evento`` es ``"<Agregado>.<operacion>"``. Lanza ``ContingenciaActivaError`` cuando el evento
    quedó respaldado (RN-29, RN-30).

    D-33: si la transacción externa ya había escrito otras filas, **no se respalda**: el rollback las descartaría y
    el evento quedaría huérfano (su sincronización fallaría siempre y bloquearía el respaldo). Se lanza la misma
    ``ContingenciaActivaError`` (503) pero sin evento; el usuario reintenta. Así todo evento respaldado es
    autosuficiente.
    """
    previas = hay_escrituras_previas()
    try:
        with transaction.atomic():
            resultado = accion()
    except (OperationalError, InterfaceError) as exc:
        if previas:
            raise ContingenciaActivaError(
                "La base de datos no está disponible; la operación no se aplicó y no quedó respaldada. Intente de nuevo"
            ) from exc
        gestor.respaldar(tipo_evento, contenido())
        raise ContingenciaActivaError(
            "La base de datos no está disponible; la operación quedó respaldada y se aplicará al recuperarse"
        ) from exc
    registrar_escritura()
    return resultado


def traducir_unico[R](accion: Callable[[], R]) -> R:
    """Convierte la violación de una restricción UNIQUE en ``DuplicadoError``; otros errores se propagan."""
    try:
        return accion()
    except IntegrityError as exc:
        causa = exc.__cause__
        if getattr(causa, "sqlstate", None) == "23505":
            restriccion = getattr(getattr(causa, "diag", None), "constraint_name", None) or ""
            campo = _CAMPOS_UNICOS.get(restriccion, restriccion or "valor")
            raise DuplicadoError(campo, f"Ya existe un registro con ese valor de {campo}") from exc
        raise


def traducir_restauracion[**P, R](restaurar: Callable[P, R]) -> Callable[P, R]:
    """Decorador de ``restaurar``: un evento respaldado malformado (JSON inválido, claves o tipos que faltan) o que
    rompe una restricción de la BD distinta de UNIQUE (``IntegrityError``/``DataError``) se convierte en
    ``ReglaNegocioError``, para que la sincronización lo trate como evento fallido (D-27, RN-30) y no como un 500.
    ``DuplicadoError``, los demás errores de dominio y las caídas de conexión pasan intactos."""

    @functools.wraps(restaurar)
    def envuelta(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return restaurar(*args, **kwargs)
        except (KeyError, ValueError, TypeError, AttributeError, ArithmeticError) as exc:
            raise ReglaNegocioError(f"El contenido del evento respaldado es inválido ({type(exc).__name__}).") from exc
        except (IntegrityError, DataError) as exc:
            raise ReglaNegocioError("El evento respaldado viola una restricción de la base de datos.") from exc

    return envuelta


def actualizado(filas: int, que: str, id: int | None) -> None:
    """Falla con ``NoEncontradoError`` si un UPDATE no tocó ninguna fila."""
    if not filas:
        raise NoEncontradoError(f"No existe {que} {id}")


def rango_del_dia(fecha: date) -> tuple[datetime, datetime]:
    """Intervalo [inicio, fin) del día calendario en America/Bogota."""
    inicio = datetime.combine(fecha, time.min, tzinfo=ZONA)
    return inicio, inicio + timedelta(days=1)


def rango_de_fechas(inicio: date, fin: date) -> tuple[datetime, datetime]:
    """Intervalo [inicio 00:00, fin + 1 día 00:00) en America/Bogota (fin incluido)."""
    return rango_del_dia(inicio)[0], rango_del_dia(fin)[1]


# --- JSON del respaldo ----------------------------------------------------------------------------


def iso(valor: date | datetime | None) -> str | None:
    return None if valor is None else valor.isoformat()


def a_fecha_hora(texto: str | None) -> datetime | None:
    if texto is None:
        return None
    valor = datetime.fromisoformat(texto)
    return valor if valor.tzinfo else valor.replace(tzinfo=UTC).astimezone(ZONA)


def a_fecha(texto: str | None) -> date | None:
    return None if texto is None else date.fromisoformat(texto)


def a_decimal(texto: str | None) -> Decimal | None:
    return None if texto is None else Decimal(texto)


def a_json(datos: dict[str, Any]) -> str:
    """Una sola línea de JSON (el medio de respaldo no admite saltos de línea)."""
    return json.dumps(datos, ensure_ascii=False, separators=(",", ":"))


def de_json(contenido: str) -> dict[str, Any]:
    return json.loads(contenido)
