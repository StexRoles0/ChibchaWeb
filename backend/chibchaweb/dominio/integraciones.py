"""Interfaces de integración externa que el dominio define y los adaptadores implementan (patrón Adapter)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING

from chibchaweb.dominio._comun import es_correo, texto_obligatorio
from chibchaweb.dominio.errores import ValidacionError

if TYPE_CHECKING:
    from chibchaweb.dominio.cuentas import MedioPago


class IdentidadExterna:
    """Datos verificados que entrega el proveedor de autenticación. Transitorio, no persistente."""

    def __init__(self, identificador_externo: str, nombre: str, correo: str, correo_verificado: bool):
        self._identificador_externo = texto_obligatorio(identificador_externo, "identificadorExterno", 255)
        self._nombre = (nombre or "").strip()
        self._correo = (correo or "").strip().lower()
        if not es_correo(self._correo):
            raise ValidacionError("correo", "El correo de la identidad no es válido")
        self._correo_verificado = bool(correo_verificado)

    @property
    def identificador_externo(self) -> str:
        return self._identificador_externo

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def correo(self) -> str:
        return self._correo

    @property
    def correo_verificado(self) -> bool:
        return self._correo_verificado

    def puede_prellenar_registro(self) -> bool:
        """El correo verificado es la condición para bloquear nombre y correo en el registro."""
        return self._correo_verificado

    def __repr__(self) -> str:
        return f"IdentidadExterna(verificada={self._correo_verificado})"


class ProveedorAutenticacion(ABC):
    """Verifica la identidad de un usuario con un proveedor OAuth 2.0 externo."""

    @abstractmethod
    def autorizar(self, codigo: str) -> IdentidadExterna:
        """Cambia el código de autorización por la identidad verificada."""


class ValidadorMedioPago(ABC):
    """Verifica un medio de pago con un servicio externo."""

    @abstractmethod
    def verificar(self, medio: MedioPago) -> bool:
        """Verifica externamente el medio de pago."""


class PasarelaPago(ABC):
    """Ejecuta un cobro ante el procesador de pagos de las franquicias."""

    @abstractmethod
    def cobrar(self, medio: MedioPago, monto: Decimal) -> str:
        """Ejecuta el cargo y devuelve la referencia; cadena vacía si fue rechazado."""


class RegistradorDominio(ABC):
    """Envía solicitudes de dominio a un registrador externo."""

    @abstractmethod
    def enviar(self, documento: str) -> None:
        """Envía el documento; lanza una excepción ante falla de red."""


class FuenteLegada(ABC):
    """Lee los registros del sistema legado.

    Cada registro es una línea ``"<TIPO>|<campos CSV>"`` con TIPO en CLIENTE, HOSTING o PAGO
    (formato anotado en pendientes-modelo.md, P-12).
    """

    @abstractmethod
    def leer_registros(self) -> list[str]:
        """Lee los registros crudos del sistema legado."""
