"""Interfaces de repositorio y unidad de trabajo (D-01, P-01, P-04, P-05).

El dominio las define; la persistencia las implementa (``MapeadorX(Mapeador[X], RepositorioX)``)
y los servicios las reciben por constructor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chibchaweb.dominio.cuentas import Cliente, Distribuidor, Empleado, Franquicia, Rol, Usuario
    from chibchaweb.dominio.dominios_web import SolicitudDominio
    from chibchaweb.dominio.facturacion import Comision, Pago
    from chibchaweb.dominio.hospedaje import PaqueteHosting, PlanPago, SitioWeb, Suscripcion
    from chibchaweb.dominio.migracion import ProcesoMigracion
    from chibchaweb.dominio.soporte import NivelServicio, Ticket


class RepositorioUsuario(ABC):
    """Agregado Usuario. Lo implementa MapeadorUsuario."""

    @abstractmethod
    def insertar(self, objeto: Usuario) -> int: ...

    @abstractmethod
    def actualizar(self, objeto: Usuario) -> None: ...

    @abstractmethod
    def buscar_por_id(self, id: int) -> Usuario: ...

    @abstractmethod
    def buscar_por_filtro(self, filtro: str) -> list[Usuario]: ...

    @abstractmethod
    def buscar_por_identificador_externo(self, identificador: str) -> Usuario | None: ...

    @abstractmethod
    def buscar_distribuidor_por_codigo(self, codigo: str) -> Distribuidor | None: ...

    @abstractmethod
    def inactivar(self, id: int) -> None: ...

    @abstractmethod
    def buscar_por_correo(self, correo: str) -> Usuario | None: ...

    @abstractmethod
    def buscar_clientes(self, filtro: str) -> list[Cliente]: ...

    @abstractmethod
    def buscar_empleados(self, filtro: str) -> list[Empleado]: ...

    @abstractmethod
    def buscar_distribuidores(self, filtro: str) -> list[Distribuidor]: ...

    @abstractmethod
    def restaurar(self, contenido: str) -> None: ...


class RepositorioSuscripcion(ABC):
    """Agregado Suscripcion (con sitio y pagos). Lo implementa MapeadorSuscripcion."""

    @abstractmethod
    def insertar(self, objeto: Suscripcion) -> int: ...

    @abstractmethod
    def actualizar(self, objeto: Suscripcion) -> None: ...

    @abstractmethod
    def buscar_por_id(self, id: int) -> Suscripcion: ...

    @abstractmethod
    def buscar_por_filtro(self, filtro: str) -> list[Suscripcion]: ...

    @abstractmethod
    def buscar_vencidas(self, fecha: date) -> list[Suscripcion]: ...

    @abstractmethod
    def registrar_pago(self, pago: Pago) -> None: ...

    @abstractmethod
    def buscar_pagos_para_comision(self, distribuidor: Distribuidor, inicio: date, fin: date) -> list[Pago]: ...

    @abstractmethod
    def buscar_sitio(self, id: int) -> SitioWeb: ...

    @abstractmethod
    def restaurar(self, contenido: str) -> None: ...


class RepositorioComision(ABC):
    """Agregado Comision (con cheque). Lo implementa MapeadorComision."""

    @abstractmethod
    def insertar(self, objeto: Comision) -> int: ...

    @abstractmethod
    def actualizar(self, objeto: Comision) -> None: ...

    @abstractmethod
    def buscar_por_id(self, id: int) -> Comision: ...

    @abstractmethod
    def buscar_por_filtro(self, filtro: str) -> list[Comision]: ...

    @abstractmethod
    def registrar_cheque(self, comision: Comision) -> None: ...

    @abstractmethod
    def restaurar(self, contenido: str) -> None: ...


class RepositorioSolicitudDominio(ABC):
    """SolicitudDominio. Lo implementa MapeadorSolicitudDominio."""

    @abstractmethod
    def insertar(self, objeto: SolicitudDominio) -> int: ...

    @abstractmethod
    def actualizar(self, objeto: SolicitudDominio) -> None: ...

    @abstractmethod
    def buscar_por_id(self, id: int) -> SolicitudDominio: ...

    @abstractmethod
    def buscar_por_filtro(self, filtro: str) -> list[SolicitudDominio]: ...

    @abstractmethod
    def buscar_por_solicitante(self, id_cliente: int) -> list[SolicitudDominio]: ...

    @abstractmethod
    def restaurar(self, contenido: str) -> None: ...


class RepositorioTicket(ABC):
    """Agregado Ticket (con movimientos). Lo implementa MapeadorTicket."""

    @abstractmethod
    def insertar(self, objeto: Ticket) -> int: ...

    @abstractmethod
    def actualizar(self, objeto: Ticket) -> None: ...

    @abstractmethod
    def buscar_por_id(self, id: int) -> Ticket: ...

    @abstractmethod
    def buscar_por_filtro(self, filtro: str) -> list[Ticket]: ...

    @abstractmethod
    def buscar_creados_el(self, fecha: date) -> list[Ticket]: ...

    @abstractmethod
    def buscar_abiertos(self) -> list[Ticket]: ...

    @abstractmethod
    def buscar_por_reportante(self, id_usuario: int) -> list[Ticket]: ...


class RepositorioMigracion(ABC):
    """Agregado ProcesoMigracion (con log). Lo implementa MapeadorMigracion."""

    @abstractmethod
    def insertar(self, objeto: ProcesoMigracion) -> int: ...

    @abstractmethod
    def actualizar(self, objeto: ProcesoMigracion) -> None: ...

    @abstractmethod
    def buscar_por_id(self, id: int) -> ProcesoMigracion: ...

    @abstractmethod
    def buscar_por_filtro(self, filtro: str) -> list[ProcesoMigracion]: ...


class RepositorioCatalogo(ABC):
    """Catálogos de solo lectura. Lo implementa MapeadorCatalogo."""

    @abstractmethod
    def listar_paquetes(self) -> list[PaqueteHosting]: ...

    @abstractmethod
    def buscar_paquete(self, id: int) -> PaqueteHosting: ...

    @abstractmethod
    def listar_planes(self) -> list[PlanPago]: ...

    @abstractmethod
    def buscar_plan(self, id: int) -> PlanPago: ...

    @abstractmethod
    def listar_franquicias(self) -> list[Franquicia]: ...

    @abstractmethod
    def buscar_franquicia(self, nombre: str) -> Franquicia: ...

    @abstractmethod
    def buscar_rol(self, id: int) -> Rol: ...

    @abstractmethod
    def buscar_nivel_inicial(self) -> NivelServicio: ...

    @abstractmethod
    def buscar_nivel_siguiente(self, actual: NivelServicio) -> NivelServicio | None: ...

    @abstractmethod
    def listar_roles(self) -> list[Rol]: ...


class UnidadDeTrabajo(ABC):
    """Agrupa escrituras en una transacción todo o nada (RN-27)."""

    @abstractmethod
    def iniciar(self) -> None: ...

    @abstractmethod
    def confirmar(self) -> None: ...

    @abstractmethod
    def revertir(self) -> None: ...
