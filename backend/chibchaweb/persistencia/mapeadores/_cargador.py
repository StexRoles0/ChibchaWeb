"""Reconstrucción de objetos del dominio a partir de filas (uso interno de los mapeadores).

Cada ``Cargador`` vive durante una sola operación y mantiene un mapa de identidad: si dos filas apuntan
al mismo cliente, sitio o distribuidor, el dominio recibe el mismo objeto. Se consulta por lotes
(``select_related`` y un ``IN`` por colección) para evitar N+1.

Profundidad del grafo (no se cargan grafos completos):
- Cliente: direcciones, tarjeta (descifrada), cuenta, distribuidor reducido (sin referidos) y, si se pide,
  sus suscripciones con sitio, paquete, plan y pagos.
- Distribuidor raíz: sus referidos como clientes sin suscripciones; las comisiones se cargan con
  ``RepositorioComision``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from django.core.exceptions import ObjectDoesNotExist

from chibchaweb.dominio.cuentas import (
    Cliente,
    CuentaAcceso,
    Direccion,
    Distribuidor,
    Empleado,
    Franquicia,
    Rol,
    TarjetaCredito,
    Usuario,
)
from chibchaweb.dominio.errores import NoEncontradoError, ValidacionError
from chibchaweb.dominio.facturacion import EstadoPago, Pago
from chibchaweb.dominio.hospedaje import PaqueteHosting, PlanPago, Plataforma, SitioWeb, Suscripcion
from chibchaweb.dominio.respaldo import AlgoritmoCifrado, GestorContingencia
from chibchaweb.dominio.soporte import NivelServicio
from chibchaweb.persistencia.modelos_orm import (
    ClienteOrm,
    DireccionOrm,
    DistribuidorOrm,
    FranquiciaOrm,
    NivelServicioOrm,
    PagoOrm,
    PaqueteHostingOrm,
    PlanPagoOrm,
    RolOrm,
    SitioWebOrm,
    SuscripcionOrm,
    UsuarioOrm,
)

RELACIONES_CLIENTE = (
    "usuario",
    "usuario__cuenta",
    "residencia",
    "facturacion",
    "medio_pago__tarjeta__franquicia",
    "distribuidor__usuario",
)


# --------------------------------------------------------------------------------------------------
# Cifrado del número de tarjeta (con los algoritmos del gestor de contingencia)
# --------------------------------------------------------------------------------------------------


def _algoritmo(gestor: GestorContingencia, nombre: str) -> AlgoritmoCifrado:
    for algoritmo in gestor.algoritmos:
        if algoritmo.nombre() == nombre:
            return algoritmo
    raise ValidacionError("algoritmo", f"El algoritmo {nombre!r} no está disponible")


def cifrar_numero(gestor: GestorContingencia, numero: str) -> tuple[str, str]:
    """Devuelve ``(algoritmo, base64(cifrado))`` con el algoritmo activo del gestor."""
    algoritmo = _algoritmo(gestor, gestor.algoritmo_activo)
    return algoritmo.nombre(), algoritmo.cifrar(numero)


def descifrar_numero(gestor: GestorContingencia, algoritmo: str, cifrado: str) -> str:
    """Descifra con el algoritmo que dice la fila."""
    return _algoritmo(gestor, algoritmo).descifrar(cifrado)


# --------------------------------------------------------------------------------------------------
# Cargador
# --------------------------------------------------------------------------------------------------


class Cargador:
    def __init__(self, gestor: GestorContingencia | None = None):
        self._gestor = gestor  # solo hace falta para descifrar tarjetas (clientes)
        self._franquicias: dict[int, Franquicia] = {}
        self._roles: dict[int, Rol] = {}
        self._paquetes: dict[int, PaqueteHosting] = {}
        self._planes: dict[int, PlanPago] = {}
        self._niveles: dict[int, NivelServicio] = {}
        self._sitios: dict[int, SitioWeb] = {}
        self._distribuidores: dict[int, Distribuidor] = {}
        self._clientes: dict[int, Cliente] = {}
        self._con_suscripciones: set[int] = set()
        self._suscripciones: dict[int, Suscripcion] = {}
        self._pagos: dict[int, Pago] = {}

    # --- catálogos y partes simples -------------------------------------------------------------
    def franquicia(self, fila: FranquiciaOrm) -> Franquicia:
        if fila.id not in self._franquicias:
            self._franquicias[fila.id] = Franquicia(fila.nombre, fila.patron_numero, id=fila.id)
        return self._franquicias[fila.id]

    def paquete(self, fila: PaqueteHostingOrm) -> PaqueteHosting:
        if fila.id not in self._paquetes:
            self._paquetes[fila.id] = PaqueteHosting(
                fila.nombre, fila.tarifa_mensual, fila.descripcion or "", id=fila.id
            )
        return self._paquetes[fila.id]

    def plan(self, fila: PlanPagoOrm) -> PlanPago:
        if fila.id not in self._planes:
            self._planes[fila.id] = PlanPago(fila.nombre, fila.meses, fila.descuento, id=fila.id)
        return self._planes[fila.id]

    def nivel(self, fila: NivelServicioOrm) -> NivelServicio:
        if fila.id not in self._niveles:
            self._niveles[fila.id] = NivelServicio(fila.nombre, fila.orden, fila.es_ultimo, id=fila.id)
        return self._niveles[fila.id]

    def rol(self, id: int) -> Rol:
        if id not in self._roles:
            fila = RolOrm.objects.prefetch_related("operaciones").filter(id=id).first()
            if fila is None:
                raise NoEncontradoError(f"No existe el rol {id}")
            self._roles[id] = self.rol_de_fila(fila)
        return self._roles[id]

    def rol_de_fila(self, fila: RolOrm) -> Rol:
        """La fila debe traer ``prefetch_related("operaciones")`` para no consultar una vez por rol."""
        if fila.id not in self._roles:
            operaciones = sorted(o.operacion for o in fila.operaciones.all())
            self._roles[fila.id] = Rol(fila.nombre, id=fila.id, operaciones=operaciones)
        return self._roles[fila.id]

    def sitio(self, fila: SitioWebOrm) -> SitioWeb:
        if fila.id not in self._sitios:
            self._sitios[fila.id] = SitioWeb(
                fila.subdominio, Plataforma(fila.plataforma), id=fila.id, dominio_propio=fila.dominio_propio
            )
        return self._sitios[fila.id]

    @staticmethod
    def direccion(fila: DireccionOrm) -> Direccion:
        return Direccion(fila.linea, fila.ciudad, fila.codigo_postal, fila.pais, id=fila.id)

    # --- usuarios -------------------------------------------------------------------------------
    def distribuidor(self, fila: DistribuidorOrm) -> Distribuidor:
        """Distribuidor reducido (sin referidos); el mismo objeto cada vez que se pide el mismo id."""
        if fila.pk not in self._distribuidores:
            u = fila.usuario
            self._distribuidores[fila.pk] = Distribuidor(
                u.nombre,
                u.correo,
                u.telefono or "",
                fila.documento,
                fila.codigo,
                id=u.id,
                activo=u.activo,
                fecha_registro=u.fecha_registro,
                fecha_modificacion=u.fecha_modificacion,
            )
        return self._distribuidores[fila.pk]

    def registrar_distribuidor(self, distribuidor: Distribuidor) -> None:
        """Usa un distribuidor ya construido (el que pasó el servicio) como la identidad de ese id."""
        self._distribuidores[distribuidor.id] = distribuidor

    def distribuidores(self, filas: Iterable[DistribuidorOrm], con_referidos: bool = True) -> list[Distribuidor]:
        resultado = [self.distribuidor(f) for f in filas]
        if con_referidos and resultado:
            referidos = (
                ClienteOrm.objects.filter(distribuidor_id__in=[d.id for d in resultado])
                .select_related(*RELACIONES_CLIENTE)
                .order_by("usuario_id")
            )
            for cliente in self.clientes(referidos, con_suscripciones=False):
                cliente.distribuidor.agregar_referido(cliente)
        return resultado

    def empleado(self, fila: UsuarioOrm) -> Empleado:
        e = fila.empleado
        return Empleado(
            fila.nombre,
            fila.correo,
            fila.telefono or "",
            e.documento,
            self.rol(e.rol_id),
            id=fila.id,
            activo=fila.activo,
            fecha_registro=fila.fecha_registro,
            fecha_modificacion=fila.fecha_modificacion,
            cuenta=None,
        )

    def clientes(self, filas: Iterable[ClienteOrm], con_suscripciones: bool = True) -> list[Cliente]:
        """Reconstruye clientes; ``filas`` debe traer ``select_related(*RELACIONES_CLIENTE)``."""
        filas = list(filas)
        resultado = []
        for fila in filas:
            if fila.pk not in self._clientes:
                self._clientes[fila.pk] = self._cliente(fila)
            resultado.append(self._clientes[fila.pk])
        if con_suscripciones:
            pendientes = {c.id: c for c in resultado if c.id not in self._con_suscripciones}
            self._cargar_suscripciones(pendientes)
        return resultado

    def _cliente(self, fila: ClienteOrm) -> Cliente:
        if self._gestor is None:
            raise ValidacionError("gestor", "Se necesita el gestor para descifrar la tarjeta del cliente")
        u = fila.usuario
        t = fila.medio_pago.tarjeta
        tarjeta = TarjetaCredito(
            descifrar_numero(self._gestor, t.algoritmo_cifrado, t.numero_cifrado),
            t.vencimiento,
            self.franquicia(t.franquicia),
            id=fila.medio_pago_id,
        )
        cliente = Cliente(
            u.nombre,
            u.correo,
            u.telefono or "",
            self.direccion(fila.residencia),
            self.direccion(fila.facturacion),
            tarjeta,
            id=u.id,
            activo=u.activo,
            fecha_registro=u.fecha_registro,
            fecha_modificacion=u.fecha_modificacion,
            distribuidor=self.distribuidor(fila.distribuidor) if fila.distribuidor_id else None,
        )
        self._reconstituir_cuenta(cliente, u)
        return cliente

    @staticmethod
    def _reconstituir_cuenta(usuario: Usuario, fila: UsuarioOrm) -> None:
        """Data Mapper: la cuenta y su titular se referencian entre sí, así que se enlazan al reconstruir."""
        try:
            c = fila.cuenta
        except ObjectDoesNotExist:
            return
        usuario._cuenta = CuentaAcceso(  # noqa: SLF001 - reconstitución desde la BD, no hay API pública
            c.identificador_externo,
            c.proveedor,
            usuario,
            id=c.id,
            fecha_vinculacion=c.fecha_vinculacion,
            ultimo_acceso=c.ultimo_acceso,
        )

    def _cargar_suscripciones(self, clientes: dict[int, Cliente]) -> None:
        if not clientes:
            return
        filas = (
            SuscripcionOrm.objects.filter(titular_id__in=list(clientes))
            .select_related("sitio", "paquete", "plan")
            .order_by("id")
        )
        nuevas: dict[int, Suscripcion] = {}
        for f in filas:
            titular = clientes[f.titular_id]
            s = Suscripcion(
                titular,
                self.sitio(f.sitio),
                self.paquete(f.paquete),
                self.plan(f.plan),
                f.fecha_inicio,
                id=f.id,
                fecha_corte=f.fecha_corte,
                activa=f.activa,
            )
            titular.agregar_suscripcion(s)
            nuevas[f.id] = s
        for p in PagoOrm.objects.filter(suscripcion_id__in=list(nuevas)).order_by("id"):
            pago = Pago(
                p.monto,
                EstadoPago(p.estado),
                nuevas[p.suscripcion_id],
                id=p.id,
                fecha=p.fecha,
                referencia_franquicia=p.referencia_franquicia,
                comisionado=p.comisionado,
            )
            nuevas[p.suscripcion_id].agregar_pago(pago)
            self._pagos[p.id] = pago
        self._suscripciones.update(nuevas)
        self._con_suscripciones.update(clientes)

    def suscripcion(self, id: int) -> Suscripcion | None:
        return self._suscripciones.get(id)

    def pago(self, id: int) -> Pago | None:
        return self._pagos.get(id)

    def usuarios(self, ids: list[int]) -> list[Usuario]:
        """Reconstruye los usuarios (de cualquier subtipo) en el orden de ``ids``; ignora los inexistentes."""
        filas = {
            f.id: f for f in UsuarioOrm.objects.filter(id__in=ids).select_related("empleado", "distribuidor", "cuenta")
        }
        por_id: dict[int, Usuario] = {}
        ids_clientes = [i for i, f in filas.items() if f.tipo == "CLIENTE"]
        if ids_clientes:
            consulta = ClienteOrm.objects.filter(usuario_id__in=ids_clientes).select_related(*RELACIONES_CLIENTE)
            por_id.update({c.id: c for c in self.clientes(consulta)})
        distribuidores = [filas[i].distribuidor for i in filas if filas[i].tipo == "DISTRIBUIDOR"]
        for d in self.distribuidores(
            DistribuidorOrm.objects.filter(pk__in=[d.pk for d in distribuidores]).select_related("usuario")
        ):
            por_id[d.id] = d
        for i, f in filas.items():
            if f.tipo == "EMPLEADO":
                empleado = self.empleado(f)
                self._reconstituir_cuenta(empleado, f)
                por_id[i] = empleado
        return [por_id[i] for i in ids if i in por_id]

    def empleados(self, ids: list[int]) -> dict[int, Empleado]:
        return {u.id: cast(Empleado, u) for u in self.usuarios(sorted(set(ids)))}
