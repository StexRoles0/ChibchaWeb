"""MapeadorMigracion: agregado ProcesoMigracion con su log."""

from __future__ import annotations

from collections.abc import Sequence

from django.db.models import Q

from chibchaweb.dominio.errores import NoEncontradoError, ValidacionError
from chibchaweb.dominio.migracion import (
    CreadorRegistroLegado,
    EntradaLog,
    EstadoMigracion,
    NivelLog,
    ProcesoMigracion,
)
from chibchaweb.dominio.repositorios import RepositorioMigracion
from chibchaweb.persistencia.mapeadores._cargador import Cargador
from chibchaweb.persistencia.mapeadores.base import Mapeador, actualizado, traducir_fallas_de_lectura
from chibchaweb.persistencia.modelos_orm import EntradaLogOrm, ProcesoMigracionOrm


@traducir_fallas_de_lectura
class MapeadorMigracion(Mapeador[ProcesoMigracion], RepositorioMigracion):
    """Recibe del contenedor los creadores de registros legados que exige ``ProcesoMigracion``."""

    def __init__(self, creadores: Sequence[CreadorRegistroLegado]):
        super().__init__("proceso_migracion")
        self._creadores = creadores

    @property
    def creadores(self) -> Sequence[CreadorRegistroLegado]:
        return self._creadores

    # --- Mapeador<ProcesoMigracion> -------------------------------------------------------------
    def insertar(self, objeto: ProcesoMigracion) -> int:
        self._exigir_ejecutor(objeto)
        fila = ProcesoMigracionOrm(
            ejecutor_id=objeto.ejecutor.id,
            fecha_inicio=objeto.fecha_inicio,
            fecha_fin=objeto.fecha_fin,
            estado=objeto.estado.value,
        )
        fila.save(force_insert=True)
        objeto.id = fila.id
        self._insertar_entradas(objeto)
        return fila.id

    def actualizar(self, objeto: ProcesoMigracion) -> None:
        self._exigir_ejecutor(objeto)
        actualizado(
            ProcesoMigracionOrm.objects.filter(id=objeto.id).update(
                fecha_inicio=objeto.fecha_inicio, fecha_fin=objeto.fecha_fin, estado=objeto.estado.value
            ),
            "el proceso de migración",
            objeto.id,
        )
        self._insertar_entradas(objeto)

    def buscar_por_id(self, id: int) -> ProcesoMigracion:
        encontrados = self._cargar(ProcesoMigracionOrm.objects.filter(id=id))
        if not encontrados:
            raise NoEncontradoError(f"No existe el proceso de migración {id}")
        return encontrados[0]

    def buscar_por_filtro(self, filtro: str) -> list[ProcesoMigracion]:
        consulta = ProcesoMigracionOrm.objects.all()
        texto = (filtro or "").strip()
        if texto:
            consulta = consulta.filter(Q(estado__icontains=texto) | Q(ejecutor__usuario__nombre__icontains=texto))
        return self._cargar(consulta)

    # --- auxiliares -----------------------------------------------------------------------------
    @staticmethod
    def _exigir_ejecutor(p: ProcesoMigracion) -> None:
        if p.ejecutor.id is None:
            raise ValidacionError("ejecutor", "El ejecutor debe estar guardado")

    @staticmethod
    def _insertar_entradas(p: ProcesoMigracion) -> None:
        """El log es solo de alta: se insertan las entradas que aún no tienen id."""
        for e in p.log:
            if e.id is None:
                fila = EntradaLogOrm(
                    proceso_id=p.id,
                    fecha=e.fecha,
                    nivel=e.nivel.value,
                    mensaje=e.mensaje,
                    identificador_legado=e.identificador_legado,
                    tipo_registro=e.tipo_registro,
                )
                fila.save(force_insert=True)
                e.id = fila.id

    def _cargar(self, consulta) -> list[ProcesoMigracion]:
        filas = list(consulta.order_by("id"))
        entradas = EntradaLogOrm.objects.filter(proceso_id__in=[f.id for f in filas]).order_by("id")
        por_proceso: dict[int, list[EntradaLog]] = {}
        for e in entradas:
            por_proceso.setdefault(e.proceso_id, []).append(
                EntradaLog(
                    NivelLog(e.nivel),
                    e.mensaje,
                    id=e.id,
                    fecha=e.fecha,
                    identificador_legado=e.identificador_legado,
                    tipo_registro=e.tipo_registro,
                )
            )
        ejecutores = Cargador().empleados([f.ejecutor_id for f in filas])
        return [
            ProcesoMigracion(
                ejecutores[f.ejecutor_id],
                list(self._creadores),
                id=f.id,
                fecha_inicio=f.fecha_inicio,
                fecha_fin=f.fecha_fin,
                estado=EstadoMigracion(f.estado),
                log=por_proceso.get(f.id, []),
            )
            for f in filas
        ]
