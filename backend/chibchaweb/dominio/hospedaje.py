"""Hospedaje (DC-MDO-01): paquetes, planes, sitios y suscripciones."""

from __future__ import annotations

import calendar
import enum
import re
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from chibchaweb.dominio._comun import a_decimal, misma_entidad, propiedad_id, redondear, texto_obligatorio
from chibchaweb.dominio.errores import EstadoInvalidoError, ReglaNegocioError, ValidacionError
from chibchaweb.dominio.facturacion import EstadoPago, Pago

if TYPE_CHECKING:
    from chibchaweb.dominio.cuentas import Cliente
    from chibchaweb.dominio.integraciones import PasarelaPago

_ETIQUETA = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_PATRON_NOMBRE_HOST = re.compile(rf"^{_ETIQUETA}(?:\.{_ETIQUETA})+$")


def _sumar_meses(fecha: date, meses: int, dia_ancla: int | None = None) -> date:
    """Suma meses a una fecha anclada a ``dia_ancla`` (por omisión, el día de ``fecha``).

    Si el día no existe en el mes destino usa el último día, sin arrastrar el ajuste al mes siguiente.
    """
    total = fecha.month - 1 + meses
    anio, mes = fecha.year + total // 12, total % 12 + 1
    return date(anio, mes, min(dia_ancla or fecha.day, calendar.monthrange(anio, mes)[1]))


class Plataforma(enum.Enum):
    """Plataformas de hospedaje ofrecidas."""

    WINDOWS = "WINDOWS"
    UNIX = "UNIX"


class PlanPago:
    """Plan de pago con su duración y descuento por compromiso."""

    id = propiedad_id()

    def __init__(self, nombre: str, meses: int, descuento: Decimal, id: int | None = None):
        self._id = id
        self._nombre = texto_obligatorio(nombre, "nombre", 40)
        if not isinstance(meses, int) or isinstance(meses, bool) or meses < 1:
            raise ValidacionError("meses", "Los meses del plan deben ser un entero positivo")
        self._meses = meses
        self._descuento = a_decimal(descuento, "descuento")
        if not Decimal("0") <= self._descuento <= Decimal("1"):
            raise ValidacionError("descuento", "El descuento debe estar entre 0 y 1")

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def meses(self) -> int:
        return self._meses

    @property
    def descuento(self) -> Decimal:
        return self._descuento

    def aplicar_descuento(self, monto: Decimal) -> Decimal:
        """Monto × (1 − descuento), redondeado a 2 decimales HALF_UP."""
        return redondear(a_decimal(monto, "monto") * (Decimal("1") - self._descuento))

    def __repr__(self) -> str:
        return f"PlanPago(id={self._id!r}, nombre={self._nombre!r})"


class PaqueteHosting:
    """Paquete de hospedaje con su tarifa mensual en USD."""

    id = propiedad_id()

    def __init__(self, nombre: str, tarifa_mensual: Decimal, descripcion: str = "", id: int | None = None):
        self._id = id
        self._nombre = texto_obligatorio(nombre, "nombre", 40)
        self._tarifa_mensual = a_decimal(tarifa_mensual, "tarifaMensual")
        if self._tarifa_mensual <= 0:
            raise ValidacionError("tarifaMensual", "La tarifa mensual debe ser mayor que cero")
        self._descripcion = descripcion or ""

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def tarifa_mensual(self) -> Decimal:
        return self._tarifa_mensual

    @property
    def descripcion(self) -> str:
        return self._descripcion

    def calcular_monto(self, plan: PlanPago) -> Decimal:
        """RN-01: tarifaMensual × meses × (1 − descuento), redondeado HALF_UP a 2 decimales."""
        return plan.aplicar_descuento(self._tarifa_mensual * plan.meses)

    def __repr__(self) -> str:
        return f"PaqueteHosting(id={self._id!r}, nombre={self._nombre!r})"


class SitioWeb:
    """Sitio hospedado: subdominio asignado, dominio propio opcional y plataforma."""

    id = propiedad_id()

    def __init__(
        self, subdominio: str, plataforma: Plataforma, id: int | None = None, dominio_propio: str | None = None
    ):
        self._id = id
        self._subdominio = self._validar_subdominio(subdominio)
        self._plataforma = self._validar_plataforma(plataforma)
        self._dominio_propio = None
        if dominio_propio:
            self.asignar_dominio_propio(dominio_propio)

    @staticmethod
    def _validar_subdominio(subdominio: str) -> str:
        valor = (subdominio or "").strip().lower()
        if len(valor) > 120 or not _PATRON_NOMBRE_HOST.match(valor):
            raise ValidacionError("sitio", "El subdominio no es un nombre de host válido")
        return valor

    @staticmethod
    def _validar_plataforma(plataforma: Plataforma) -> Plataforma:
        if not isinstance(plataforma, Plataforma):
            raise ValidacionError("plataforma", "La plataforma debe ser WINDOWS o UNIX")
        return plataforma

    @property
    def subdominio(self) -> str:
        return self._subdominio

    @subdominio.setter
    def subdominio(self, valor: str) -> None:
        self._subdominio = self._validar_subdominio(valor)

    @property
    def dominio_propio(self) -> str | None:
        return self._dominio_propio

    @property
    def plataforma(self) -> Plataforma:
        return self._plataforma

    @plataforma.setter
    def plataforma(self, valor: Plataforma) -> None:
        self._plataforma = self._validar_plataforma(valor)

    def asignar_dominio_propio(self, dominio: str) -> None:
        valor = (dominio or "").strip().lower()
        if not _PATRON_NOMBRE_HOST.match(valor):
            raise ValidacionError("dominio", "El dominio propio no es válido")
        if self._dominio_propio is not None and self._dominio_propio != valor:
            raise ReglaNegocioError("El sitio ya tiene un dominio propio")
        self._dominio_propio = valor

    def tiene_dominio_propio(self) -> bool:
        return self._dominio_propio is not None

    def __repr__(self) -> str:
        return f"SitioWeb(id={self._id!r}, subdominio={self._subdominio!r})"


class Suscripcion:
    """Contrato de hospedaje: une sitio, paquete y plan, y lleva el ciclo de cobro."""

    id = propiedad_id()

    def __init__(
        self,
        titular: Cliente,
        sitio: SitioWeb,
        paquete: PaqueteHosting,
        plan: PlanPago,
        fecha_inicio: date,
        id: int | None = None,
        fecha_corte: date | None = None,
        activa: bool = True,
        pagos: list[Pago] | None = None,
    ):
        for campo, valor in (("titular", titular), ("sitio", sitio), ("paquete", paquete), ("plan", plan)):
            if valor is None:
                raise ValidacionError(campo, f"El campo {campo} es obligatorio")
        if not isinstance(fecha_inicio, date):
            raise ValidacionError("fechaInicio", "La fecha de inicio es obligatoria")
        self._id = id
        self._titular = titular
        self._sitio = sitio
        self._paquete = paquete
        self._plan = plan
        self._fecha_inicio = fecha_inicio
        self._fecha_corte = fecha_corte or fecha_inicio  # RN-04
        if self._fecha_corte < self._fecha_inicio:
            raise ValidacionError("fechaCorte", "La fecha de corte no puede ser anterior al inicio")
        self._activa = bool(activa)
        self._pagos: list[Pago] = list(pagos or [])

    @property
    def fecha_inicio(self) -> date:
        return self._fecha_inicio

    @property
    def fecha_corte(self) -> date:
        return self._fecha_corte

    @property
    def activa(self) -> bool:
        return self._activa

    @property
    def titular(self) -> Cliente:
        return self._titular

    @property
    def sitio(self) -> SitioWeb:
        return self._sitio

    @property
    def paquete(self) -> PaqueteHosting:
        return self._paquete

    @property
    def plan(self) -> PlanPago:
        return self._plan

    @property
    def pagos(self) -> tuple[Pago, ...]:
        return tuple(self._pagos)

    def monto_del_periodo(self) -> Decimal:
        return self._paquete.calcular_monto(self._plan)

    def esta_vencida(self, fecha: date) -> bool:
        """RN-02: vencida si fechaCorte ≤ fecha."""
        return self._fecha_corte <= fecha

    def avanzar_corte(self) -> None:
        """RN-03: suma plan.meses a la fecha de corte."""
        self._fecha_corte = _sumar_meses(self._fecha_corte, self._plan.meses, self._fecha_inicio.day)

    def cambiar_paquete(self, nuevo: PaqueteHosting) -> None:
        self._exigir_activa()
        if nuevo is None:
            raise ValidacionError("paquete", "El paquete es obligatorio")
        self._paquete = nuevo

    def cambiar_plan(self, nuevo: PlanPago) -> None:
        self._exigir_activa()
        if nuevo is None:
            raise ValidacionError("plan", "El plan es obligatorio")
        self._plan = nuevo

    def agregar_pago(self, pago: Pago) -> None:
        if pago.suscripcion is not self and not misma_entidad(pago.suscripcion, self):
            raise ReglaNegocioError("El pago corresponde a otra suscripción")
        if not any(p is pago or misma_entidad(p, pago) for p in self._pagos):
            self._pagos.append(pago)

    def suspender(self) -> None:
        self._activa = False

    def cobrar(self, pasarela: PasarelaPago) -> Pago:
        """RN-03: cobra el periodo; EXITOSO avanza el corte, FALLIDO no lo mueve ni detiene el lote."""
        self._exigir_activa()
        monto = self.monto_del_periodo()
        medio = self._titular.medio_pago
        referencia = ""
        if medio.esta_vigente():
            try:
                referencia = (pasarela.cobrar(medio, monto) or "").strip()
            except Exception:  # falla del procesador: el cargo no se completó
                referencia = ""
        if referencia:
            pago = Pago(monto, EstadoPago.EXITOSO, self, referencia_franquicia=referencia)
        else:
            pago = Pago(monto, EstadoPago.FALLIDO, self)
        self.agregar_pago(pago)
        if pago.es_exitoso():
            self.avanzar_corte()
        return pago

    def _exigir_activa(self) -> None:
        if not self._activa:
            raise EstadoInvalidoError("La suscripción no está activa")

    def __repr__(self) -> str:
        return f"Suscripcion(id={self._id!r}, corte={self._fecha_corte.isoformat()}, activa={self._activa})"
