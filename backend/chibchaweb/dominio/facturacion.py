"""Facturación y comisiones (DC-MDO-01): pagos, comisiones, cheques y categorías de distribuidor."""

from __future__ import annotations

import enum
import re
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from chibchaweb.dominio._comun import a_decimal, ahora, misma_entidad, propiedad_id, redondear, texto_obligatorio
from chibchaweb.dominio.errores import ReglaNegocioError, ValidacionError

if TYPE_CHECKING:
    from chibchaweb.dominio.cuentas import Distribuidor
    from chibchaweb.dominio.hospedaje import Suscripcion

_PATRON_NUMERO_CHEQUE = re.compile(r"^CHQ-[0-9]{4}-[0-9]{6,}$")  # RN-21


class EstadoPago(enum.Enum):
    """Resultados posibles de un cobro."""

    EXITOSO = "EXITOSO"
    FALLIDO = "FALLIDO"


class Pago:
    """Resultado de un intento de cobro periódico sobre una suscripción."""

    id = propiedad_id()

    def __init__(
        self,
        monto: Decimal,
        estado: EstadoPago,
        suscripcion: Suscripcion,
        id: int | None = None,
        fecha: datetime | None = None,
        referencia_franquicia: str | None = None,
        comisionado: bool = False,
    ):
        self._id = id
        self._monto = a_decimal(monto, "monto")
        if self._monto <= 0:
            raise ValidacionError("monto", "El monto del pago debe ser mayor que cero")
        if not isinstance(estado, EstadoPago):
            raise ValidacionError("estado", "Estado de pago inválido")
        if suscripcion is None:
            raise ValidacionError("suscripcion", "El pago necesita una suscripción")
        referencia = (referencia_franquicia or "").strip() or None
        if estado is EstadoPago.EXITOSO and referencia is None:
            raise ValidacionError("referenciaFranquicia", "Un pago exitoso necesita la referencia del procesador")
        if estado is EstadoPago.FALLIDO and (referencia is not None or comisionado):
            raise ValidacionError("estado", "Un pago fallido no tiene referencia ni sustenta comisiones")
        if referencia is not None and len(referencia) > 100:
            raise ValidacionError("referenciaFranquicia", "La referencia admite máximo 100 caracteres")
        self._estado = estado
        self._suscripcion = suscripcion
        self._fecha = fecha or ahora()
        self._referencia_franquicia = referencia
        self._comisionado = bool(comisionado)

    @property
    def monto(self) -> Decimal:
        return self._monto

    @property
    def fecha(self) -> datetime:
        return self._fecha

    @property
    def estado(self) -> EstadoPago:
        return self._estado

    @property
    def referencia_franquicia(self) -> str | None:
        return self._referencia_franquicia

    @property
    def comisionado(self) -> bool:
        return self._comisionado

    @property
    def suscripcion(self) -> Suscripcion:
        return self._suscripcion

    def es_exitoso(self) -> bool:
        return self._estado is EstadoPago.EXITOSO

    def esta_disponible_para_comision(self) -> bool:
        return self.es_exitoso() and not self._comisionado

    def marcar_comisionado(self) -> None:
        if not self.esta_disponible_para_comision():
            raise ReglaNegocioError("El pago no está disponible para comisión")
        self._comisionado = True

    def __repr__(self) -> str:
        return f"Pago(id={self._id!r}, monto={self._monto}, estado={self._estado.value})"


class Cheque:
    """Cheque emitido a un distribuidor por el monto de una comisión. Su emisión es irreversible."""

    id = propiedad_id()

    def __init__(self, numero: str, beneficiario: str, monto: Decimal, fecha_emision: date, id: int | None = None):
        self._id = id
        numero = texto_obligatorio(numero, "numero", 30)
        if not _PATRON_NUMERO_CHEQUE.match(numero):
            raise ValidacionError("numero", "El número de cheque debe tener la forma CHQ-<año>-<id de 6 dígitos>")
        self._numero = numero
        self._beneficiario = texto_obligatorio(beneficiario, "beneficiario", 120)
        self._monto = redondear(a_decimal(monto, "monto"))
        if self._monto <= 0:
            raise ValidacionError("monto", "El monto del cheque debe ser mayor que cero")
        if not isinstance(fecha_emision, date):
            raise ValidacionError("fechaEmision", "La fecha de emisión es obligatoria")
        self._fecha_emision = fecha_emision

    @property
    def numero(self) -> str:
        return self._numero

    @property
    def beneficiario(self) -> str:
        return self._beneficiario

    @property
    def monto(self) -> Decimal:
        return self._monto

    @property
    def fecha_emision(self) -> date:
        return self._fecha_emision

    def monto_en_letras(self) -> str:
        """RN-21: p. ej. ``CINCUENTA Y CUATRO DÓLARES CON 00/100``."""
        enteros = int(self._monto)
        centavos = int((self._monto - enteros) * 100)
        if enteros == 1:
            moneda = "UN DÓLAR"
        else:
            palabras = _apocopar(_en_letras(enteros))
            de = " DE" if enteros >= 1_000_000 and enteros % 1_000_000 == 0 else ""
            moneda = f"{palabras}{de} DÓLARES"
        return f"{moneda} CON {centavos:02d}/100"

    def __repr__(self) -> str:
        return f"Cheque(id={self._id!r}, numero={self._numero!r}, monto={self._monto})"


class Comision:
    """Liquidación de un periodo para un distribuidor, con categoría y porcentaje históricos."""

    id = propiedad_id()

    def __init__(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        clientes_referidos: int,
        nombre_categoria: str,
        porcentaje: Decimal,
        beneficiario: Distribuidor,
        id: int | None = None,
        pagos_base: list[Pago] | None = None,
        cheque: Cheque | None = None,
    ):
        if not isinstance(fecha_inicio, date) or not isinstance(fecha_fin, date):
            raise ValidacionError("fechaInicio", "El periodo de la comisión es obligatorio")
        if fecha_fin < fecha_inicio:
            raise ValidacionError("fechaFin", "La fecha fin no puede ser anterior a la de inicio")
        if not isinstance(clientes_referidos, int) or clientes_referidos < 0:
            raise ValidacionError("clientesReferidos", "Los clientes referidos deben ser un entero ≥ 0")
        if beneficiario is None:
            raise ValidacionError("beneficiario", "La comisión necesita un beneficiario")
        self._id = id
        self._fecha_inicio = fecha_inicio
        self._fecha_fin = fecha_fin
        self._clientes_referidos = clientes_referidos
        self._nombre_categoria = texto_obligatorio(nombre_categoria, "nombreCategoria", 20)
        self._porcentaje = a_decimal(porcentaje, "porcentaje")
        if not Decimal("0") < self._porcentaje <= Decimal("1"):
            raise ValidacionError("porcentaje", "El porcentaje debe estar entre 0 y 1")
        self._beneficiario = beneficiario
        self._pagos_base: list[Pago] = list(pagos_base or [])
        self._cheque = cheque

    @property
    def fecha_inicio(self) -> date:
        return self._fecha_inicio

    @property
    def fecha_fin(self) -> date:
        return self._fecha_fin

    @property
    def clientes_referidos(self) -> int:
        return self._clientes_referidos

    @property
    def nombre_categoria(self) -> str:
        return self._nombre_categoria

    @property
    def porcentaje(self) -> Decimal:
        return self._porcentaje

    @property
    def beneficiario(self) -> Distribuidor:
        return self._beneficiario

    @property
    def pagos_base(self) -> tuple[Pago, ...]:
        return tuple(self._pagos_base)

    @property
    def cheque(self) -> Cheque | None:
        return self._cheque

    def agregar_pago_base(self, pago: Pago) -> None:
        """RN-20: solo pagos exitosos, sin comisionar, del periodo y de un referido del beneficiario."""
        if not pago.esta_disponible_para_comision():
            raise ReglaNegocioError("El pago no está disponible para comisión")
        fecha = pago.fecha.date() if isinstance(pago.fecha, datetime) else pago.fecha
        if not self._fecha_inicio <= fecha <= self._fecha_fin:
            raise ReglaNegocioError("El pago está fuera del periodo liquidado")
        if not misma_entidad(pago.suscripcion.titular.distribuidor, self._beneficiario):
            raise ReglaNegocioError("El pago no es de un cliente referido por el distribuidor")
        pago.marcar_comisionado()
        self._pagos_base.append(pago)

    def calcular_monto(self) -> Decimal:
        """RN-20: Σ pagosBase × porcentaje, redondeado HALF_UP."""
        return redondear(sum((p.monto for p in self._pagos_base), Decimal("0")) * self._porcentaje)

    def asociar_cheque(self, cheque: Cheque) -> None:
        """RN-21: falla si la comisión ya tiene cheque o si el monto no coincide."""
        if self.tiene_cheque():
            raise ReglaNegocioError("La comisión ya tiene un cheque emitido")
        if not self._pagos_base:
            raise ReglaNegocioError("La comisión no tiene pagos base")
        if cheque.monto != self.calcular_monto():
            raise ReglaNegocioError("El monto del cheque no coincide con el de la comisión")
        self._cheque = cheque

    def tiene_cheque(self) -> bool:
        return self._cheque is not None

    def __repr__(self) -> str:
        return f"Comision(id={self._id!r}, categoria={self._nombre_categoria!r}, pagos={len(self._pagos_base)})"


class CategoriaDistribuidor(ABC):
    """Estrategia que determina la categoría del distribuidor y su porcentaje (Strategy)."""

    @abstractmethod
    def nombre(self) -> str:
        """Nombre de la categoría."""

    @abstractmethod
    def porcentaje(self) -> Decimal:
        """Porcentaje de comisión."""

    @abstractmethod
    def aplica_a(self, cantidad_referidos: int) -> bool:
        """Indica si la categoría corresponde a la cantidad de referidos."""


def _exigir_cantidad(cantidad_referidos: int) -> None:
    if not isinstance(cantidad_referidos, int) or cantidad_referidos < 0:
        raise ValidacionError("cantidadReferidos", "La cantidad de referidos debe ser un entero ≥ 0")


class CategoriaBasica(CategoriaDistribuidor):
    """Básica: hasta 100 referidos, 10 % (RN-19)."""

    def __init__(self):
        self._porcentaje_comision = Decimal("0.10")
        self._limite_superior = 100

    @property
    def porcentaje_comision(self) -> Decimal:
        return self._porcentaje_comision

    @property
    def limite_superior(self) -> int:
        return self._limite_superior

    def nombre(self) -> str:
        return "Básico"

    def porcentaje(self) -> Decimal:
        return self._porcentaje_comision

    def aplica_a(self, cantidad_referidos: int) -> bool:
        _exigir_cantidad(cantidad_referidos)
        return cantidad_referidos <= self._limite_superior


class CategoriaPremium(CategoriaDistribuidor):
    """Premium: 101 o más referidos, 15 % (RN-19)."""

    def __init__(self):
        self._porcentaje_comision = Decimal("0.15")
        self._limite_inferior = 101

    @property
    def porcentaje_comision(self) -> Decimal:
        return self._porcentaje_comision

    @property
    def limite_inferior(self) -> int:
        return self._limite_inferior

    def nombre(self) -> str:
        return "Premium"

    def porcentaje(self) -> Decimal:
        return self._porcentaje_comision

    def aplica_a(self, cantidad_referidos: int) -> bool:
        _exigir_cantidad(cantidad_referidos)
        return cantidad_referidos >= self._limite_inferior


# --------------------------------------------------------------------------------------------------
# Números en letras (español) para el cheque
# --------------------------------------------------------------------------------------------------

_UNIDADES = (
    "CERO UNO DOS TRES CUATRO CINCO SEIS SIETE OCHO NUEVE DIEZ ONCE DOCE TRECE CATORCE QUINCE "
    "DIECISÉIS DIECISIETE DIECIOCHO DIECINUEVE VEINTE VEINTIUNO VEINTIDÓS VEINTITRÉS VEINTICUATRO "
    "VEINTICINCO VEINTISÉIS VEINTISIETE VEINTIOCHO VEINTINUEVE"
).split()
_DECENAS = ("", "", "", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA")
_CENTENAS = (
    "",
    "CIENTO",
    "DOSCIENTOS",
    "TRESCIENTOS",
    "CUATROCIENTOS",
    "QUINIENTOS",
    "SEISCIENTOS",
    "SETECIENTOS",
    "OCHOCIENTOS",
    "NOVECIENTOS",
)


def _menor_que_mil(n: int) -> str:
    if n == 100:
        return "CIEN"
    centenas, resto = divmod(n, 100)
    partes = [_CENTENAS[centenas]] if centenas else []
    if resto:
        if resto < 30:
            partes.append(_UNIDADES[resto])
        else:
            decenas, unidades = divmod(resto, 10)
            partes.append(_DECENAS[decenas] + (f" Y {_UNIDADES[unidades]}" if unidades else ""))
    return " ".join(partes)


def _en_letras(n: int) -> str:
    if n == 0:
        return "CERO"
    millones, resto = divmod(n, 1_000_000)
    miles, unidades = divmod(resto, 1000)
    partes = []
    if millones:
        partes.append("UN MILLÓN" if millones == 1 else f"{_apocopar(_en_letras(millones))} MILLONES")
    if miles:
        partes.append("MIL" if miles == 1 else f"{_apocopar(_menor_que_mil(miles))} MIL")
    if unidades:
        partes.append(_menor_que_mil(unidades))
    return " ".join(partes)


def _apocopar(texto: str) -> str:
    """'UNO' pierde la vocal delante de un sustantivo: VEINTIÚN DÓLARES, TREINTA Y UN MIL."""
    if texto.endswith("VEINTIUNO"):
        return texto[: -len("VEINTIUNO")] + "VEINTIÚN"
    if texto.endswith("UNO"):
        return texto[:-1]
    return texto
