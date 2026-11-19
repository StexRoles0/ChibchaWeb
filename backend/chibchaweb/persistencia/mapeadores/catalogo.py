"""MapeadorCatalogo: catálogos de solo lectura (paquetes, planes, franquicias, roles y niveles de servicio)."""

from __future__ import annotations

from chibchaweb.dominio.cuentas import Franquicia, Rol
from chibchaweb.dominio.errores import NoEncontradoError
from chibchaweb.dominio.hospedaje import PaqueteHosting, PlanPago
from chibchaweb.dominio.repositorios import RepositorioCatalogo
from chibchaweb.dominio.soporte import NivelServicio
from chibchaweb.persistencia.mapeadores._cargador import Cargador
from chibchaweb.persistencia.mapeadores.base import traducir_fallas_de_lectura
from chibchaweb.persistencia.modelos_orm import (
    FranquiciaOrm,
    NivelServicioOrm,
    PaqueteHostingOrm,
    PlanPagoOrm,
    RolOrm,
)


@traducir_fallas_de_lectura
class MapeadorCatalogo(RepositorioCatalogo):
    """Solo lectura; no hereda de ``Mapeador<T>`` (el modelo no lo indica)."""

    def listar_paquetes(self) -> list[PaqueteHosting]:
        cargador = Cargador()
        return [cargador.paquete(f) for f in PaqueteHostingOrm.objects.order_by("id")]

    def buscar_paquete(self, id: int) -> PaqueteHosting:
        fila = PaqueteHostingOrm.objects.filter(id=id).first()
        if fila is None:
            raise NoEncontradoError(f"No existe el paquete {id}")
        return Cargador().paquete(fila)

    def listar_planes(self) -> list[PlanPago]:
        cargador = Cargador()
        return [cargador.plan(f) for f in PlanPagoOrm.objects.order_by("id")]

    def buscar_plan(self, id: int) -> PlanPago:
        fila = PlanPagoOrm.objects.filter(id=id).first()
        if fila is None:
            raise NoEncontradoError(f"No existe el plan {id}")
        return Cargador().plan(fila)

    def listar_franquicias(self) -> list[Franquicia]:
        cargador = Cargador()
        return [cargador.franquicia(f) for f in FranquiciaOrm.objects.order_by("id")]

    def buscar_franquicia(self, nombre: str) -> Franquicia:
        fila = FranquiciaOrm.objects.filter(nombre=(nombre or "").strip().upper()).first()
        if fila is None:
            raise NoEncontradoError(f"No existe la franquicia {nombre}")
        return Cargador().franquicia(fila)

    def buscar_rol(self, id: int) -> Rol:
        return Cargador().rol(id)

    def buscar_nivel_inicial(self) -> NivelServicio:
        fila = NivelServicioOrm.objects.filter(orden=1).first()
        if fila is None:
            raise NoEncontradoError("No existe el nivel de servicio de orden 1")
        return Cargador().nivel(fila)

    def buscar_nivel_siguiente(self, actual: NivelServicio) -> NivelServicio | None:
        fila = NivelServicioOrm.objects.filter(orden__gt=actual.orden).order_by("orden").first()
        return Cargador().nivel(fila) if fila is not None else None

    def listar_roles(self) -> list[Rol]:
        cargador = Cargador()
        return [cargador.rol_de_fila(f) for f in RolOrm.objects.prefetch_related("operaciones").order_by("id")]
