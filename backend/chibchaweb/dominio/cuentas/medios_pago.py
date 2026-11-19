"""Cuentas y perfiles (DC-MDO-01): direcciones, medios de pago y franquicias."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import date
from typing import TYPE_CHECKING

from chibchaweb.dominio._comun import hoy, propiedad_id, texto_obligatorio
from chibchaweb.dominio.errores import ValidacionError

if TYPE_CHECKING:
    from chibchaweb.dominio.integraciones import ValidadorMedioPago

_PATRON_CODIGO_POSTAL = re.compile(r"^[A-Za-z0-9]{4,10}$")  # RN-10
_PATRON_CODIGO_SEGURIDAD = re.compile(r"^[0-9]{3,4}$")  # modelo: 3 o 4 dígitos (P-11)


# --------------------------------------------------------------------------------------------------
# Dirección y medios de pago
# --------------------------------------------------------------------------------------------------


class Direccion:
    """Dirección postal de un cliente (residencia o facturación)."""

    id = propiedad_id()

    def __init__(self, linea: str, ciudad: str, codigo_postal: str, pais: str = "Colombia", id: int | None = None):
        self._id = id
        self._linea = (linea or "").strip()
        self._ciudad = (ciudad or "").strip()
        self._codigo_postal = (codigo_postal or "").strip()
        self._pais = (pais or "").strip()

    @property
    def linea(self) -> str:
        return self._linea

    @property
    def ciudad(self) -> str:
        return self._ciudad

    @property
    def codigo_postal(self) -> str:
        return self._codigo_postal

    @property
    def pais(self) -> str:
        return self._pais

    def validar(self) -> bool:
        """Campos obligatorios completos; código postal alfanumérico de 4 a 10 (RN-10)."""
        return (
            0 < len(self._linea) <= 150
            and 0 < len(self._ciudad) <= 80
            and 0 < len(self._pais) <= 60
            and _PATRON_CODIGO_POSTAL.match(self._codigo_postal) is not None
        )

    def __repr__(self) -> str:
        return f"Direccion(id={self._id!r}, ciudad={self._ciudad!r})"


class MedioPago(ABC):
    """Medio con el que se cobra a un cliente (Strategy por polimorfismo)."""

    id = propiedad_id()

    def __init__(self, id: int | None = None):
        self._id = id

    @abstractmethod
    def validar(self, validador: ValidadorMedioPago) -> bool:
        """Valida el medio de pago con el verificador externo."""

    @abstractmethod
    def esta_vigente(self) -> bool:
        """Indica si el medio puede usarse para cobrar."""

    @abstractmethod
    def descripcion(self) -> str:
        """Representación segura del medio para mostrar."""


class TarjetaCredito(MedioPago):
    """Tarjeta de crédito de una franquicia aceptada.

    El código de seguridad solo vive en memoria hasta que se valida; después se descarta (RN-12).
    Ni el número completo ni el código aparecen en ``repr``.
    """

    def __init__(
        self,
        numero: str,
        vencimiento: date,
        franquicia: Franquicia,
        codigo_seguridad: str | None = None,
        id: int | None = None,
    ):
        super().__init__(id)
        self._numero = re.sub(r"[\s-]", "", numero or "")
        if not re.fullmatch(r"[0-9]{13,19}", self._numero):
            raise ValidacionError("numeroTarjeta", "El número de tarjeta debe tener de 13 a 19 dígitos")
        if not isinstance(vencimiento, date):
            raise ValidacionError("vencimiento", "La fecha de vencimiento es obligatoria")
        self._vencimiento = vencimiento
        if franquicia is None:
            raise ValidacionError("franquicia", "La franquicia es obligatoria")
        self._franquicia = franquicia
        self._codigo_seguridad = (codigo_seguridad or "").strip() or None

    @property
    def numero(self) -> str:
        """Número completo: solo para el validador, la pasarela y el cifrado del mapeador."""
        return self._numero

    @property
    def vencimiento(self) -> date:
        return self._vencimiento

    @property
    def codigo_seguridad(self) -> str | None:
        """Código transitorio; es None después de validar o si la tarjeta se reconstruyó."""
        return self._codigo_seguridad

    @property
    def franquicia(self) -> Franquicia:
        return self._franquicia

    def validar(self, validador: ValidadorMedioPago) -> bool:
        """RN-11, en orden: patrón de la franquicia, vigencia, código de seguridad y verificación externa."""
        try:
            if not self._franquicia.reconoce_numero(self._numero):
                raise ValidacionError("numeroTarjeta", f"El número no corresponde a {self._franquicia.nombre}")
            if not self.esta_vigente():
                raise ValidacionError("vencimiento", "La tarjeta está vencida")
            if not _PATRON_CODIGO_SEGURIDAD.match(self._codigo_seguridad or ""):
                raise ValidacionError("codigoSeguridad", "El código de seguridad no es válido")
            if not validador.verificar(self):
                raise ValidacionError("numeroTarjeta", "El verificador externo rechazó la tarjeta")
            return True
        finally:
            self._codigo_seguridad = None  # RN-12: nunca se conserva

    def esta_vigente(self) -> bool:
        """Vigente si el vencimiento es ≥ al primer día del mes actual (RN-11 b)."""
        return self._vencimiento >= hoy().replace(day=1)

    def descripcion(self) -> str:
        """Número enmascarado, p. ej. ``VISA •••• 4242`` (RN-12)."""
        return f"{self._franquicia.nombre} •••• {self._numero[-4:]}"

    def __repr__(self) -> str:
        return f"TarjetaCredito(id={self._id!r}, {self.descripcion()!r})"


class Franquicia:
    """Franquicia de tarjeta aceptada con el patrón que reconoce sus números."""

    id = propiedad_id()

    def __init__(self, nombre: str, patron_numero: str, id: int | None = None):
        self._id = id
        self._nombre = texto_obligatorio(nombre, "nombre", 20).upper()
        self._patron_numero = texto_obligatorio(patron_numero, "patronNumero", 100)
        try:
            self._regex = re.compile(self._patron_numero)
        except re.error as exc:
            raise ValidacionError("patronNumero", "El patrón de la franquicia no es una expresión válida") from exc

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def patron_numero(self) -> str:
        return self._patron_numero

    def reconoce_numero(self, numero: str) -> bool:
        return self._regex.fullmatch(re.sub(r"[\s-]", "", numero or "")) is not None

    def __repr__(self) -> str:
        return f"Franquicia(id={self._id!r}, nombre={self._nombre!r})"
