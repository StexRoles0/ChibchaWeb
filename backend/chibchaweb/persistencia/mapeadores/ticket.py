"""MapeadorTicket: agregado Ticket con sus movimientos."""

from __future__ import annotations

from datetime import date

from django.db.models import Q

from chibchaweb.dominio.errores import NoEncontradoError, ValidacionError
from chibchaweb.dominio.repositorios import RepositorioTicket
from chibchaweb.dominio.respaldo import GestorContingencia
from chibchaweb.dominio.soporte import CategoriaTicket, EstadoTicket, MovimientoTicket, Ticket
from chibchaweb.persistencia.mapeadores._cargador import Cargador
from chibchaweb.persistencia.mapeadores.base import Mapeador, actualizado, rango_del_dia, traducir_fallas_de_lectura
from chibchaweb.persistencia.modelos_orm import MovimientoTicketOrm, TicketOrm


@traducir_fallas_de_lectura
class MapeadorTicket(Mapeador[Ticket], RepositorioTicket):
    """Sin contingencia (RT04 solo cubre 4 mapeadores). Recibe el gestor únicamente para descifrar la tarjeta
    de los clientes reportantes al reconstruirlos (P-18)."""

    def __init__(self, gestor: GestorContingencia):
        super().__init__("ticket")
        self._gestor = gestor

    @property
    def gestor(self) -> GestorContingencia:
        return self._gestor

    # --- Mapeador<Ticket> -----------------------------------------------------------------------
    def insertar(self, objeto: Ticket) -> int:
        self._exigir_guardados(objeto)
        fila = TicketOrm(
            reportante_id=objeto.reportante.id,
            sitio_afectado_id=objeto.sitio_afectado.id if objeto.sitio_afectado is not None else None,
            nivel_actual_id=objeto.nivel_actual.id,
            descripcion=objeto.descripcion,
            fecha_creacion=objeto.fecha_creacion,
            categoria=objeto.categoria.value,
            estado=objeto.estado.value,
        )
        fila.save(force_insert=True)
        objeto.id = fila.id
        self._insertar_movimientos(objeto)
        return fila.id

    def actualizar(self, objeto: Ticket) -> None:
        self._exigir_guardados(objeto)
        actualizado(
            TicketOrm.objects.filter(id=objeto.id).update(
                nivel_actual_id=objeto.nivel_actual.id,
                estado=objeto.estado.value,
                descripcion=objeto.descripcion,
                categoria=objeto.categoria.value,
            ),
            "el ticket",
            objeto.id,
        )
        self._insertar_movimientos(objeto)

    def buscar_por_id(self, id: int) -> Ticket:
        encontrados = self._cargar(TicketOrm.objects.filter(id=id))
        if not encontrados:
            raise NoEncontradoError(f"No existe el ticket {id}")
        return encontrados[0]

    def buscar_por_filtro(self, filtro: str) -> list[Ticket]:
        consulta = TicketOrm.objects.all()
        texto = (filtro or "").strip()
        if texto:
            consulta = consulta.filter(
                Q(descripcion__icontains=texto)
                | Q(categoria__icontains=texto)
                | Q(estado__icontains=texto)
                | Q(reportante__nombre__icontains=texto)
            )
        return self._cargar(consulta)

    # --- RepositorioTicket ----------------------------------------------------------------------
    def buscar_creados_el(self, fecha: date) -> list[Ticket]:
        inicio, fin = rango_del_dia(fecha)
        return self._cargar(TicketOrm.objects.filter(fecha_creacion__gte=inicio, fecha_creacion__lt=fin))

    def buscar_abiertos(self) -> list[Ticket]:
        return self._cargar(TicketOrm.objects.exclude(estado=EstadoTicket.RESUELTO.value))

    def buscar_por_reportante(self, id_usuario: int) -> list[Ticket]:
        return self._cargar(TicketOrm.objects.filter(reportante_id=id_usuario))

    # --- auxiliares -----------------------------------------------------------------------------
    @staticmethod
    def _exigir_guardados(t: Ticket) -> None:
        if t.reportante.id is None or t.nivel_actual.id is None:
            raise ValidacionError("ticket", "El reportante y el nivel deben estar guardados")
        if t.sitio_afectado is not None and t.sitio_afectado.id is None:
            raise ValidacionError("sitio", "El sitio afectado debe estar guardado")
        if any(m.responsable.id is None or m.nivel_resultante.id is None for m in t.movimientos):
            raise ValidacionError("movimientos", "El responsable y el nivel de cada movimiento deben estar guardados")

    @staticmethod
    def _insertar_movimientos(t: Ticket) -> None:
        """Los movimientos son solo de alta: se insertan los que aún no tienen id."""
        for m in t.movimientos:
            if m.id is None:
                fila = MovimientoTicketOrm(
                    ticket_id=t.id,
                    responsable_id=m.responsable.id,
                    nivel_resultante_id=m.nivel_resultante.id,
                    fecha=m.fecha,
                    observacion=m.observacion,
                    estado_resultante=m.estado_resultante.value,
                )
                fila.save(force_insert=True)
                m.id = fila.id

    def _cargar(self, consulta) -> list[Ticket]:
        filas = list(consulta.select_related("nivel_actual", "sitio_afectado").order_by("id"))
        movimientos = list(
            MovimientoTicketOrm.objects.filter(ticket_id__in=[f.id for f in filas])
            .select_related("nivel_resultante")
            .order_by("id")
        )
        cargador = Cargador(self._gestor)
        usuarios = {u.id: u for u in cargador.usuarios(sorted({f.reportante_id for f in filas}))}
        empleados = cargador.empleados([m.responsable_id for m in movimientos])
        por_ticket: dict[int, list[MovimientoTicket]] = {}
        for m in movimientos:
            por_ticket.setdefault(m.ticket_id, []).append(
                MovimientoTicket(
                    m.observacion or "",
                    EstadoTicket(m.estado_resultante),
                    cargador.nivel(m.nivel_resultante),
                    empleados[m.responsable_id],
                    id=m.id,
                    fecha=m.fecha,
                )
            )
        return [
            Ticket(
                f.descripcion,
                CategoriaTicket(f.categoria),
                usuarios[f.reportante_id],
                cargador.nivel(f.nivel_actual),
                id=f.id,
                fecha_creacion=f.fecha_creacion,
                estado=EstadoTicket(f.estado),
                sitio_afectado=cargador.sitio(f.sitio_afectado) if f.sitio_afectado_id else None,
                movimientos=por_ticket.get(f.id, []),
            )
            for f in filas
        ]
