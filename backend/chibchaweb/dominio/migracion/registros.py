"""Migración (DC-MDO-01): registros legados (productos) y sus creadores (Factory Method).

Formato de los datos de cada registro (P-12): una línea CSV sin el tipo.
- CLIENTE: identificador, nombre, correo, "linea, ciudad, codigo postal", numero_tarjeta, telefono,
  vencimiento (AAAA-MM-DD), franquicia
- HOSTING: identificador, identificador_cliente, subdominio, paquete, plan, plataforma
- PAGO: identificador, identificador_cliente, monto, fecha (AAAA-MM-DD), referencia
"""

from __future__ import annotations

import csv
import re
from abc import ABC, abstractmethod
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

from chibchaweb.dominio._comun import (
    PATRON_TELEFONO,
    ZONA,
    es_correo,
    hoy,
)
from chibchaweb.dominio.cuentas import Cliente, Direccion, Franquicia, TarjetaCredito
from chibchaweb.dominio.errores import ReglaNegocioError
from chibchaweb.dominio.facturacion import EstadoPago, Pago
from chibchaweb.dominio.hospedaje import PaqueteHosting, PlanPago, Plataforma, SitioWeb, Suscripcion

_PATRON_SUBDOMINIO = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$")


def _campos(datos: str, cantidad: int) -> list[str]:
    """Parte una línea CSV y completa con cadenas vacías hasta la cantidad esperada."""
    filas = list(csv.reader([datos or ""]))
    valores = [v.strip() for v in (filas[0] if filas else [])]
    return (valores + [""] * cantidad)[:cantidad]


def _fecha(texto: str) -> date | None:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return None


def _decimal(texto: str) -> Decimal | None:
    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


# --------------------------------------------------------------------------------------------------
# Productos del Factory Method
# --------------------------------------------------------------------------------------------------


class RegistroLegado(ABC):
    """Registro leído del sistema legado; cada subtipo aplica sus reglas de validación."""

    def __init__(self, identificador_legado: str):
        self._identificador_legado = (identificador_legado or "").strip()
        self._valido = False
        self._errores: list[str] = []

    @property
    def identificador_legado(self) -> str:
        return self._identificador_legado

    @property
    def valido(self) -> bool:
        return self._valido

    @abstractmethod
    def validar(self) -> bool:
        """Aplica las reglas del subtipo y actualiza valido."""

    def describir_errores(self) -> str:
        return "; ".join(self._errores)

    # --- auxiliares para los subtipos y el proceso --------------------------------------------
    def _iniciar_validacion(self) -> None:
        self._errores = []
        if not self._identificador_legado:
            self._errores.append("Falta el identificador legado")

    def _terminar_validacion(self) -> bool:
        self._valido = not self._errores
        return self._valido

    def _invalidar(self, error: str) -> None:
        self._errores.append(error)
        self._valido = False

    def _exigir_valido(self) -> None:
        if not self._valido:
            raise ReglaNegocioError(f"El registro {self._identificador_legado} no es válido")


class ClienteLegado(RegistroLegado):
    """Registro legado con los datos de un cliente."""

    def __init__(
        self,
        identificador_legado: str,
        nombre: str,
        correo: str,
        direccion: str,
        numero_tarjeta: str,
        telefono: str,
        vencimiento_tarjeta: date | None,
        franquicia: str,
        franquicias: list[Franquicia] | None = None,
    ):
        super().__init__(identificador_legado)
        self._nombre = (nombre or "").strip()
        self._correo = (correo or "").strip().lower()
        self._direccion = (direccion or "").strip()
        self._numero_tarjeta = re.sub(r"[\s-]", "", numero_tarjeta or "")
        self._telefono = (telefono or "").strip()
        self._vencimiento_tarjeta = vencimiento_tarjeta
        self._franquicia = (franquicia or "").strip().upper()
        self._franquicias = {f.nombre: f for f in franquicias or []}  # catálogo actual

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def correo(self) -> str:
        return self._correo

    @property
    def direccion(self) -> str:
        return self._direccion

    @property
    def numero_tarjeta(self) -> str:
        return self._numero_tarjeta

    @property
    def telefono(self) -> str:
        return self._telefono

    @property
    def vencimiento_tarjeta(self) -> date | None:
        return self._vencimiento_tarjeta

    @property
    def franquicia(self) -> str:
        return self._franquicia

    def _direccion_partes(self) -> Direccion | None:
        partes = [p.strip() for p in self._direccion.rsplit(",", 2)]
        return Direccion(*partes) if len(partes) == 3 else None

    def validar(self) -> bool:
        """Valida correo, dirección y tarjeta (franquicia del catálogo, patrón y vigencia; RN-28)."""
        self._iniciar_validacion()
        if not self._nombre or len(self._nombre) > 120:
            self._errores.append("Nombre vacío o demasiado largo")
        if not es_correo(self._correo):
            self._errores.append("Correo inválido")
        if not PATRON_TELEFONO.match(self._telefono):
            self._errores.append("Teléfono inválido")
        direccion = self._direccion_partes()
        if direccion is None or not direccion.validar():
            self._errores.append("Dirección inválida")
        franquicia = self._franquicias.get(self._franquicia)
        if franquicia is None:
            self._errores.append(f"Franquicia {self._franquicia or '(vacía)'} no existe en el catálogo")
        elif not franquicia.reconoce_numero(self._numero_tarjeta):
            self._errores.append("El número de tarjeta no corresponde a la franquicia")
        if self._vencimiento_tarjeta is None or self._vencimiento_tarjeta < hoy().replace(day=1):
            self._errores.append("Tarjeta vencida o sin fecha de vencimiento")
        return self._terminar_validacion()

    def a_cliente(self) -> Cliente:
        """Construye el Cliente con sus direcciones y tarjeta, sin cuenta de acceso (RN-28)."""
        self._exigir_valido()
        tarjeta = TarjetaCredito(self._numero_tarjeta, self._vencimiento_tarjeta, self._franquicias[self._franquicia])
        return Cliente(
            nombre=self._nombre,
            correo=self._correo,
            telefono=self._telefono,
            residencia=self._direccion_partes(),
            facturacion=self._direccion_partes(),
            medio_pago=tarjeta,
        )


class HostingLegado(RegistroLegado):
    """Registro legado de un servicio de hospedaje, validado contra el catálogo actual (RF08)."""

    def __init__(
        self,
        identificador_legado: str,
        identificador_cliente: str,
        subdominio: str,
        paquete: str,
        plan: str,
        plataforma: str,
        paquetes: list[PaqueteHosting] | None = None,
        planes: list[PlanPago] | None = None,
    ):
        super().__init__(identificador_legado)
        self._identificador_cliente = (identificador_cliente or "").strip()
        self._subdominio = (subdominio or "").strip().lower()
        self._paquete = (paquete or "").strip()
        self._plan = (plan or "").strip()
        self._plataforma = (plataforma or "").strip().upper()
        self._paquetes = {p.nombre: p for p in paquetes or []}
        self._planes = {p.nombre: p for p in planes or []}

    @property
    def identificador_cliente(self) -> str:
        return self._identificador_cliente

    @property
    def subdominio(self) -> str:
        return self._subdominio

    @property
    def paquete(self) -> str:
        return self._paquete

    @property
    def plan(self) -> str:
        return self._plan

    @property
    def plataforma(self) -> str:
        return self._plataforma

    def validar(self) -> bool:
        """Paquete, plan y plataforma deben existir en el catálogo actual."""
        self._iniciar_validacion()
        if not self._identificador_cliente:
            self._errores.append("Falta el identificador del cliente")
        if len(self._subdominio) > 120 or not _PATRON_SUBDOMINIO.match(self._subdominio):
            self._errores.append("Subdominio inválido")
        if self._paquete not in self._paquetes:
            self._errores.append(f"El paquete {self._paquete or '(vacío)'} no existe en el catálogo")
        if self._plan not in self._planes:
            self._errores.append(f"El plan {self._plan or '(vacío)'} no existe en el catálogo")
        if self._plataforma not in Plataforma.__members__:
            self._errores.append(f"La plataforma {self._plataforma or '(vacía)'} no existe")
        return self._terminar_validacion()

    def a_suscripcion(self, titular: Cliente, paquete: PaqueteHosting, plan: PlanPago) -> Suscripcion:
        """Construye la Suscripcion y su SitioWeb, y la agrega al titular."""
        self._exigir_valido()
        if paquete.nombre != self._paquete or plan.nombre != self._plan:
            raise ReglaNegocioError("El paquete o el plan no corresponden al registro legado")
        sitio = SitioWeb(self._subdominio, Plataforma[self._plataforma])
        suscripcion = Suscripcion(titular, sitio, paquete, plan, fecha_inicio=hoy())
        titular.agregar_suscripcion(suscripcion)
        return suscripcion


class PagoLegado(RegistroLegado):
    """Registro legado del historial de pagos de un cliente."""

    def __init__(
        self,
        identificador_legado: str,
        identificador_cliente: str,
        monto: Decimal | None,
        fecha: date | None,
        referencia: str,
    ):
        super().__init__(identificador_legado)
        self._identificador_cliente = (identificador_cliente or "").strip()
        self._monto = monto
        self._fecha = fecha
        self._referencia = (referencia or "").strip()

    @property
    def identificador_cliente(self) -> str:
        return self._identificador_cliente

    @property
    def monto(self) -> Decimal | None:
        return self._monto

    @property
    def fecha(self) -> date | None:
        return self._fecha

    @property
    def referencia(self) -> str:
        return self._referencia

    def validar(self) -> bool:
        """Monto > 0 y fecha no futura (y referencia, que el Pago exitoso necesita)."""
        self._iniciar_validacion()
        if not self._identificador_cliente:
            self._errores.append("Falta el identificador del cliente")
        if self._monto is None or not self._monto.is_finite() or self._monto <= 0:
            self._errores.append("Monto inválido")
        if self._fecha is None or self._fecha > hoy():
            self._errores.append("Fecha inválida o futura")
        if not self._referencia or len(self._referencia) > 100:
            self._errores.append("Referencia vacía o demasiado larga")
        return self._terminar_validacion()

    def a_pago(self, suscripcion: Suscripcion) -> Pago:
        """Construye el Pago exitoso, marcado como comisionado, y lo agrega a la suscripción."""
        self._exigir_valido()
        pago = Pago(
            self._monto,
            EstadoPago.EXITOSO,
            suscripcion,
            fecha=datetime.combine(self._fecha, time(), tzinfo=ZONA),
            referencia_franquicia=self._referencia,
            comisionado=True,
        )
        suscripcion.agregar_pago(pago)
        return pago


# --------------------------------------------------------------------------------------------------
# Creadores del Factory Method
# --------------------------------------------------------------------------------------------------


class CreadorRegistroLegado(ABC):
    """Creador abstracto: declara el método fábrica del subtipo de registro."""

    @abstractmethod
    def tipo(self) -> str:
        """Tipo de registro que atiende."""

    @abstractmethod
    def crear_registro(self, datos: str) -> RegistroLegado:
        """Método fábrica: instancia el subtipo de registro."""

    def procesar(self, datos: str) -> RegistroLegado:
        """Crea el registro con el método fábrica, lo valida y lo devuelve."""
        registro = self.crear_registro(datos)
        registro.validar()
        return registro


class CreadorClienteLegado(CreadorRegistroLegado):
    """Instancia registros ClienteLegado. Recibe el catálogo de franquicias para validar."""

    def __init__(self, franquicias: list[Franquicia]):
        self._franquicias = list(franquicias)

    def tipo(self) -> str:
        return "CLIENTE"

    def crear_registro(self, datos: str) -> RegistroLegado:
        ident, nombre, correo, direccion, numero, telefono, vencimiento, franquicia = _campos(datos, 8)
        return ClienteLegado(
            ident, nombre, correo, direccion, numero, telefono, _fecha(vencimiento), franquicia, self._franquicias
        )


class CreadorHostingLegado(CreadorRegistroLegado):
    """Instancia registros HostingLegado. Recibe los catálogos de paquetes y planes."""

    def __init__(self, paquetes: list[PaqueteHosting], planes: list[PlanPago]):
        self._paquetes = list(paquetes)
        self._planes = list(planes)

    def tipo(self) -> str:
        return "HOSTING"

    def crear_registro(self, datos: str) -> RegistroLegado:
        ident, cliente, subdominio, paquete, plan, plataforma = _campos(datos, 6)
        return HostingLegado(ident, cliente, subdominio, paquete, plan, plataforma, self._paquetes, self._planes)


class CreadorPagoLegado(CreadorRegistroLegado):
    """Instancia registros PagoLegado."""

    def tipo(self) -> str:
        return "PAGO"

    def crear_registro(self, datos: str) -> RegistroLegado:
        ident, cliente, monto, fecha, referencia = _campos(datos, 5)
        return PagoLegado(ident, cliente, _decimal(monto), _fecha(fecha), referencia)
