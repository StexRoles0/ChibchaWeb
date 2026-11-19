"""Dobles de prueba en memoria: un Repositorio*EnMemoria por interfaz, UnidadDeTrabajo falsa y
adaptadores falsos de las 5 interfaces de integración (comportamiento de D-06).

Los usan las pruebas del dominio y, en las fases siguientes, las del servicio.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from chibchaweb.dominio.cuentas import Cliente, Distribuidor, Empleado, Franquicia, MedioPago, Rol, Usuario
from chibchaweb.dominio.dominios_web import SolicitudDominio
from chibchaweb.dominio.errores import AutorizacionFallidaError, ErrorDominio, NoEncontradoError
from chibchaweb.dominio.facturacion import Comision, Pago
from chibchaweb.dominio.hospedaje import PaqueteHosting, PlanPago, SitioWeb, Suscripcion
from chibchaweb.dominio.integraciones import (
    FuenteLegada,
    IdentidadExterna,
    PasarelaPago,
    ProveedorAutenticacion,
    RegistradorDominio,
    ValidadorMedioPago,
)
from chibchaweb.dominio.migracion import ProcesoMigracion
from chibchaweb.dominio.repositorios import (
    RepositorioCatalogo,
    RepositorioComision,
    RepositorioMigracion,
    RepositorioSolicitudDominio,
    RepositorioSuscripcion,
    RepositorioTicket,
    RepositorioUsuario,
    UnidadDeTrabajo,
)
from chibchaweb.dominio.soporte import NivelServicio, Ticket

# --------------------------------------------------------------------------------------------------
# Catálogo estándar (igual a docs/schema.sql y seed_dev.sql)
# --------------------------------------------------------------------------------------------------


def paquetes_estandar() -> list[PaqueteHosting]:
    return [
        PaqueteHosting("Chibcha-Plata", Decimal("5.00"), "Paquete básico", id=1),
        PaqueteHosting("Chibcha-Oro", Decimal("10.00"), "Paquete intermedio", id=2),
        PaqueteHosting("Chibcha-Platino", Decimal("20.00"), "Paquete completo", id=3),
    ]


def planes_estandar() -> list[PlanPago]:
    return [
        PlanPago("Mensual", 1, Decimal("0.00"), id=1),
        PlanPago("Trimestral", 3, Decimal("0.05"), id=2),
        PlanPago("Semestral", 6, Decimal("0.10"), id=3),
        PlanPago("Anual", 12, Decimal("0.15"), id=4),
    ]


def franquicias_estandar() -> list[Franquicia]:
    return [
        Franquicia("VISA", r"^4[0-9]{12}([0-9]{3})?$", id=1),
        Franquicia("MASTERCARD", r"^(5[1-5][0-9]{14}|2[2-7][0-9]{14})$", id=2),
        Franquicia("DINERS", r"^3(0[0-5]|[68][0-9])[0-9]{11}$", id=3),
    ]


def niveles_estandar() -> list[NivelServicio]:
    return [
        NivelServicio("Soporte", 1, False, id=1),
        NivelServicio("Gestión", 2, False, id=2),
        NivelServicio("Desarrollo", 3, True, id=3),
    ]


def roles_estandar() -> list[Rol]:
    return [
        Rol(
            "Gestión", 1, ["GESTIONAR_EMPLEADOS", "GESTIONAR_DISTRIBUIDORES", "CONSULTAR_REGISTROS", "REGISTRAR_TICKET"]
        ),
        Rol("Soporte", 2, ["ATENDER_TICKETS", "REGISTRAR_TICKET"]),
        Rol("Administrador", 3, ["MIGRAR_DATOS", "GESTIONAR_CONTINGENCIA", "REGISTRAR_TICKET"]),
    ]


# --------------------------------------------------------------------------------------------------
# Base común de los repositorios en memoria
# --------------------------------------------------------------------------------------------------


class _AlmacenEnMemoria:
    """Guarda los objetos por id. Simula fallas de BD con ``fallar_con`` (p. ej. ContingenciaActivaError)."""

    def __init__(self):
        self.objetos: dict[int, object] = {}
        self.restaurados: list[str] = []
        self.fallar_con: Exception | None = None
        self.fallar_restaurar_en: int | None = None  # índice (0-based) del restaurar que falla
        self._siguiente = 1

    def _quizas_fallar(self) -> None:
        if self.fallar_con is not None:
            raise self.fallar_con

    def _guardar_nuevo(self, objeto) -> int:
        self._quizas_fallar()
        if objeto.id is None:
            objeto.id = self._siguiente
        self._siguiente = max(self._siguiente, objeto.id) + 1
        self.objetos[objeto.id] = objeto
        return objeto.id

    def _guardar(self, objeto) -> None:
        self._quizas_fallar()
        if objeto.id not in self.objetos:
            raise NoEncontradoError(f"No existe el objeto {objeto.id}")
        self.objetos[objeto.id] = objeto

    def _buscar(self, id: int):
        try:
            return self.objetos[id]
        except KeyError:
            raise NoEncontradoError(f"No existe el objeto {id}") from None

    def _restaurar(self, contenido: str) -> None:
        if self.fallar_restaurar_en is not None and len(self.restaurados) == self.fallar_restaurar_en:
            raise ErrorDominio("Falla simulada al restaurar")
        self.restaurados.append(contenido)

    @staticmethod
    def _coincide(filtro: str, *textos: object) -> bool:
        filtro = (filtro or "").lower()
        return not filtro or any(filtro in str(t).lower() for t in textos if t is not None)


# --------------------------------------------------------------------------------------------------
# Repositorios en memoria
# --------------------------------------------------------------------------------------------------


class RepositorioUsuarioEnMemoria(_AlmacenEnMemoria, RepositorioUsuario):
    def insertar(self, objeto: Usuario) -> int:
        return self._guardar_nuevo(objeto)

    def actualizar(self, objeto: Usuario) -> None:
        self._guardar(objeto)

    def buscar_por_id(self, id: int) -> Usuario:
        return self._buscar(id)

    def buscar_por_filtro(self, filtro: str) -> list[Usuario]:
        return [
            u
            for u in self.objetos.values()
            # igual que el mapeador: nombre, correo, documento y código del distribuidor
            if self._coincide(filtro, u.nombre, u.correo, getattr(u, "documento", None), getattr(u, "codigo", None))
        ]

    def buscar_por_identificador_externo(self, identificador: str) -> Usuario | None:
        return next(
            (u for u in self.objetos.values() if u.cuenta is not None and u.cuenta.coincide_con(identificador)), None
        )

    def buscar_distribuidor_por_codigo(self, codigo: str) -> Distribuidor | None:
        return next(
            (u for u in self.objetos.values() if isinstance(u, Distribuidor) and u.activo and u.codigo == codigo),
            None,
        )

    def inactivar(self, id: int) -> None:
        self._quizas_fallar()
        self._buscar(id).inactivar()

    def buscar_por_correo(self, correo: str) -> Usuario | None:
        correo = (correo or "").strip().lower()
        return next((u for u in self.objetos.values() if u.correo == correo), None)

    def buscar_clientes(self, filtro: str) -> list[Cliente]:
        return [u for u in self.buscar_por_filtro(filtro) if isinstance(u, Cliente)]

    def buscar_empleados(self, filtro: str) -> list[Empleado]:
        return [u for u in self.buscar_por_filtro(filtro) if isinstance(u, Empleado)]

    def buscar_distribuidores(self, filtro: str) -> list[Distribuidor]:
        return [u for u in self.buscar_por_filtro(filtro) if isinstance(u, Distribuidor)]

    def restaurar(self, contenido: str) -> None:
        self._restaurar(contenido)


class RepositorioSuscripcionEnMemoria(_AlmacenEnMemoria, RepositorioSuscripcion):
    def __init__(self):
        super().__init__()
        self.pagos: dict[int, Pago] = {}

    def insertar(self, objeto: Suscripcion) -> int:
        if objeto.sitio.id is None:
            objeto.sitio.id = len(self.objetos) + 1
        return self._guardar_nuevo(objeto)

    def actualizar(self, objeto: Suscripcion) -> None:
        self._guardar(objeto)

    def buscar_por_id(self, id: int) -> Suscripcion:
        return self._buscar(id)

    def buscar_por_filtro(self, filtro: str) -> list[Suscripcion]:
        return [s for s in self.objetos.values() if self._coincide(filtro, s.sitio.subdominio, s.titular.nombre)]

    def buscar_vencidas(self, fecha: date) -> list[Suscripcion]:
        return [s for s in self.objetos.values() if s.activa and s.esta_vencida(fecha)]

    def registrar_pago(self, pago: Pago) -> None:
        self._quizas_fallar()
        if pago.id is None:
            pago.id = len(self.pagos) + 1
        self.pagos[pago.id] = pago

    def buscar_pagos_para_comision(self, distribuidor: Distribuidor, inicio: date, fin: date) -> list[Pago]:
        resultado = []
        for suscripcion in self.objetos.values():
            titular_distribuidor = suscripcion.titular.distribuidor
            if titular_distribuidor is None or titular_distribuidor.id != distribuidor.id:
                continue
            for pago in suscripcion.pagos:
                fecha = pago.fecha.date() if isinstance(pago.fecha, datetime) else pago.fecha
                if pago.esta_disponible_para_comision() and inicio <= fecha <= fin:
                    resultado.append(pago)
        return resultado

    def buscar_sitio(self, id: int) -> SitioWeb:
        for suscripcion in self.objetos.values():
            if suscripcion.sitio.id == id:
                return suscripcion.sitio
        raise NoEncontradoError(f"No existe el sitio {id}")

    def restaurar(self, contenido: str) -> None:
        self._restaurar(contenido)


class RepositorioComisionEnMemoria(_AlmacenEnMemoria, RepositorioComision):
    def __init__(self):
        super().__init__()
        self.cheques_registrados: list[int] = []

    def insertar(self, objeto: Comision) -> int:
        return self._guardar_nuevo(objeto)

    def actualizar(self, objeto: Comision) -> None:
        self._guardar(objeto)

    def buscar_por_id(self, id: int) -> Comision:
        return self._buscar(id)

    def buscar_por_filtro(self, filtro: str) -> list[Comision]:
        return [c for c in self.objetos.values() if self._coincide(filtro, c.beneficiario.nombre, c.nombre_categoria)]

    def registrar_cheque(self, comision: Comision) -> None:
        self._quizas_fallar()
        if comision.cheque is not None and comision.cheque.id is None:
            comision.cheque.id = len(self.cheques_registrados) + 1
        self.cheques_registrados.append(comision.id)

    def restaurar(self, contenido: str) -> None:
        self._restaurar(contenido)


class RepositorioSolicitudDominioEnMemoria(_AlmacenEnMemoria, RepositorioSolicitudDominio):
    def insertar(self, objeto: SolicitudDominio) -> int:
        return self._guardar_nuevo(objeto)

    def actualizar(self, objeto: SolicitudDominio) -> None:
        self._guardar(objeto)

    def buscar_por_id(self, id: int) -> SolicitudDominio:
        return self._buscar(id)

    def buscar_por_filtro(self, filtro: str) -> list[SolicitudDominio]:
        return [s for s in self.objetos.values() if self._coincide(filtro, s.nombre_completo(), s.estado.value)]

    def buscar_por_solicitante(self, id_cliente: int) -> list[SolicitudDominio]:
        return [s for s in self.objetos.values() if s.solicitante.id == id_cliente]

    def restaurar(self, contenido: str) -> None:
        self._restaurar(contenido)


class RepositorioTicketEnMemoria(_AlmacenEnMemoria, RepositorioTicket):
    def insertar(self, objeto: Ticket) -> int:
        return self._guardar_nuevo(objeto)

    def actualizar(self, objeto: Ticket) -> None:
        self._guardar(objeto)

    def buscar_por_id(self, id: int) -> Ticket:
        return self._buscar(id)

    def buscar_por_filtro(self, filtro: str) -> list[Ticket]:
        return [t for t in self.objetos.values() if self._coincide(filtro, t.descripcion, t.categoria.value)]

    def buscar_creados_el(self, fecha: date) -> list[Ticket]:
        return [t for t in self.objetos.values() if t.fecha_creacion.date() == fecha]

    def buscar_abiertos(self) -> list[Ticket]:
        return [t for t in self.objetos.values() if t.esta_abierto()]

    def buscar_por_reportante(self, id_usuario: int) -> list[Ticket]:
        return [t for t in self.objetos.values() if t.reportante.id == id_usuario]


class RepositorioMigracionEnMemoria(_AlmacenEnMemoria, RepositorioMigracion):
    def insertar(self, objeto: ProcesoMigracion) -> int:
        return self._guardar_nuevo(objeto)

    def actualizar(self, objeto: ProcesoMigracion) -> None:
        self._guardar(objeto)

    def buscar_por_id(self, id: int) -> ProcesoMigracion:
        return self._buscar(id)

    def buscar_por_filtro(self, filtro: str) -> list[ProcesoMigracion]:
        return [p for p in self.objetos.values() if self._coincide(filtro, p.estado.value)]


class RepositorioCatalogoEnMemoria(RepositorioCatalogo):
    """Catálogos de solo lectura; por defecto, los mismos de schema.sql."""

    def __init__(
        self,
        paquetes: list[PaqueteHosting] | None = None,
        planes: list[PlanPago] | None = None,
        franquicias: list[Franquicia] | None = None,
        roles: list[Rol] | None = None,
        niveles: list[NivelServicio] | None = None,
    ):
        self.paquetes = paquetes if paquetes is not None else paquetes_estandar()
        self.planes = planes if planes is not None else planes_estandar()
        self.franquicias = franquicias if franquicias is not None else franquicias_estandar()
        self.roles = roles if roles is not None else roles_estandar()
        self.niveles = sorted(niveles if niveles is not None else niveles_estandar(), key=lambda n: n.orden)

    @staticmethod
    def _por_id(objetos, id: int, que: str):
        for objeto in objetos:
            if objeto.id == id:
                return objeto
        raise NoEncontradoError(f"No existe {que} {id}")

    def listar_paquetes(self) -> list[PaqueteHosting]:
        return list(self.paquetes)

    def buscar_paquete(self, id: int) -> PaqueteHosting:
        return self._por_id(self.paquetes, id, "el paquete")

    def listar_planes(self) -> list[PlanPago]:
        return list(self.planes)

    def buscar_plan(self, id: int) -> PlanPago:
        return self._por_id(self.planes, id, "el plan")

    def listar_franquicias(self) -> list[Franquicia]:
        return list(self.franquicias)

    def buscar_franquicia(self, nombre: str) -> Franquicia:
        for franquicia in self.franquicias:
            if franquicia.nombre == (nombre or "").upper():
                return franquicia
        raise NoEncontradoError(f"No existe la franquicia {nombre}")

    def buscar_rol(self, id: int) -> Rol:
        return self._por_id(self.roles, id, "el rol")

    def buscar_nivel_inicial(self) -> NivelServicio:
        return self.niveles[0]

    def buscar_nivel_siguiente(self, actual: NivelServicio) -> NivelServicio | None:
        return next((n for n in self.niveles if n.orden > actual.orden), None)

    def listar_roles(self) -> list[Rol]:
        return list(self.roles)


class UnidadDeTrabajoEnMemoria(UnidadDeTrabajo):
    """Registra las llamadas para que las pruebas comprueben el todo o nada."""

    def __init__(self):
        self.llamadas: list[str] = []
        self.activa = False

    def iniciar(self) -> None:
        self.llamadas.append("iniciar")
        self.activa = True

    def confirmar(self) -> None:
        self.llamadas.append("confirmar")
        self.activa = False

    def revertir(self) -> None:
        self.llamadas.append("revertir")
        self.activa = False


# --------------------------------------------------------------------------------------------------
# Adaptadores falsos (D-05, D-06)
# --------------------------------------------------------------------------------------------------


class ProveedorAutenticacionFalso(ProveedorAutenticacion):
    """``dev:<correo>`` devuelve una identidad verificada con ``sub = "dev|<correo>"`` (D-05).

    ``dev-noverificado:<correo>`` devuelve la identidad con el correo sin verificar.
    """

    def autorizar(self, codigo: str) -> IdentidadExterna:
        prefijo, _, correo = (codigo or "").partition(":")
        if prefijo not in ("dev", "dev-noverificado") or not correo:
            raise AutorizacionFallidaError("Código de autorización inválido")
        nombre = correo.split("@")[0].replace(".", " ").title()
        return IdentidadExterna(f"dev|{correo}", nombre, correo, prefijo == "dev")


class ValidadorMedioPagoFalso(ValidadorMedioPago):
    """Rechaza las tarjetas que terminan en 0002 (D-06)."""

    def __init__(self):
        self.verificados: list[MedioPago] = []

    def verificar(self, medio: MedioPago) -> bool:
        self.verificados.append(medio)
        return not getattr(medio, "numero", "").endswith("0002")


class PasarelaPagoFalsa(PasarelaPago):
    """Rechaza las tarjetas que terminan en 0341; si no, devuelve ``REF-<uuid8>`` (D-06)."""

    def __init__(self):
        self.cobros: list[tuple[MedioPago, Decimal]] = []

    def cobrar(self, medio: MedioPago, monto: Decimal) -> str:
        self.cobros.append((medio, monto))
        if getattr(medio, "numero", "").endswith("0341"):
            return ""
        return f"REF-{uuid.uuid4().hex[:8]}"


class RegistradorDominioFalso(RegistradorDominio):
    """Rechaza (falla de red simulada) los dominios que contienen ``rechazo`` (D-06)."""

    def __init__(self):
        self.enviados: list[str] = []

    def enviar(self, documento: str) -> None:
        if "rechazo" in documento:
            raise ConnectionError("Falla de red simulada en el registrador")
        self.enviados.append(documento)


class FuenteLegadaFalsa(FuenteLegada):
    """Fuente legada en memoria: devuelve las líneas ``TIPO|csv`` que se le den (P-12)."""

    def __init__(self, registros: list[str] | None = None):
        self.registros = list(registros or [])

    def leer_registros(self) -> list[str]:
        return list(self.registros)
