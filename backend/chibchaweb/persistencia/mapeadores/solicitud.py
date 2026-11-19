"""MapeadorSolicitudDominio: solicitudes de registro de dominio propio."""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Q

from chibchaweb.dominio.dominios_web import EstadoSolicitud, SolicitudDominio
from chibchaweb.dominio.errores import NoEncontradoError, ValidacionError
from chibchaweb.dominio.repositorios import RepositorioSolicitudDominio
from chibchaweb.dominio.respaldo import GestorContingencia
from chibchaweb.persistencia.mapeadores._cargador import RELACIONES_CLIENTE, Cargador
from chibchaweb.persistencia.mapeadores.base import (
    Mapeador,
    a_fecha_hora,
    a_json,
    actualizado,
    con_contingencia,
    de_json,
    iso,
    traducir_fallas_de_lectura,
    traducir_restauracion,
)
from chibchaweb.persistencia.modelos_orm import ClienteOrm, SolicitudDominioOrm


@traducir_fallas_de_lectura
class MapeadorSolicitudDominio(Mapeador[SolicitudDominio], RepositorioSolicitudDominio):
    """Respalda las solicitudes ya enviadas ante una caída de la BD (RT04)."""

    def __init__(self, gestor: GestorContingencia):
        super().__init__("solicitud_dominio")
        self._gestor = gestor

    @property
    def gestor(self) -> GestorContingencia:
        return self._gestor

    # --- Mapeador<SolicitudDominio> -------------------------------------------------------------
    def insertar(self, objeto: SolicitudDominio) -> int:
        datos = self._a_datos(objeto, "insertar", con_ids=False)
        respaldo = a_json(datos)

        def accion() -> int:
            self._escribir_insertar(datos)
            return datos["id"]

        id = con_contingencia(self._gestor, "SolicitudDominio.insertar", lambda: respaldo, accion)
        objeto.id = id
        return id

    def actualizar(self, objeto: SolicitudDominio) -> None:
        datos = self._a_datos(objeto, "actualizar", con_ids=True)
        respaldo = a_json(datos)
        con_contingencia(
            self._gestor, "SolicitudDominio.actualizar", lambda: respaldo, lambda: self._escribir_actualizar(datos)
        )

    def buscar_por_id(self, id: int) -> SolicitudDominio:
        encontradas = self._cargar(SolicitudDominioOrm.objects.filter(id=id))
        if not encontradas:
            raise NoEncontradoError(f"No existe la solicitud de dominio {id}")
        return encontradas[0]

    def buscar_por_filtro(self, filtro: str) -> list[SolicitudDominio]:
        consulta = SolicitudDominioOrm.objects.all()
        texto = (filtro or "").strip()
        if texto:
            consulta = consulta.filter(
                Q(nombre__icontains=texto)
                | Q(extension__icontains=texto)
                | Q(estado__icontains=texto)
                | Q(solicitante__usuario__nombre__icontains=texto)
            )
        return self._cargar(consulta)

    # --- RepositorioSolicitudDominio ------------------------------------------------------------
    def buscar_por_solicitante(self, id_cliente: int) -> list[SolicitudDominio]:
        return self._cargar(SolicitudDominioOrm.objects.filter(solicitante_id=id_cliente))

    @traducir_restauracion
    def restaurar(self, contenido: str) -> None:
        """Reaplica el evento respaldado (insertar o actualizar); no vuelve a respaldar."""
        datos = de_json(contenido)
        with transaction.atomic():
            if datos["_operacion"] == "insertar":
                self._escribir_insertar(datos)
            else:
                self._escribir_actualizar(datos)

    # --- consultas ------------------------------------------------------------------------------
    def _cargar(self, consulta) -> list[SolicitudDominio]:
        filas = list(consulta.order_by("id"))
        cargador = Cargador(self._gestor)
        solicitantes = cargador.clientes(
            ClienteOrm.objects.filter(usuario_id__in={f.solicitante_id for f in filas}).select_related(
                *RELACIONES_CLIENTE
            ),
            con_suscripciones=False,
        )
        por_id = {c.id: c for c in solicitantes}
        return [
            SolicitudDominio(
                f.nombre,
                f.extension,
                por_id[f.solicitante_id],
                id=f.id,
                fecha_solicitud=f.fecha_solicitud,
                fecha_envio=f.fecha_envio,
                estado=EstadoSolicitud(f.estado),
            )
            for f in filas
        ]

    # --- dominio -> datos / datos -> filas ------------------------------------------------------
    @staticmethod
    def _a_datos(s: SolicitudDominio, operacion: str, con_ids: bool) -> dict[str, Any]:
        if s.solicitante.id is None:
            raise ValidacionError("solicitante", "El solicitante debe estar guardado")
        return {
            "_operacion": operacion,
            "id": s.id if con_ids else None,
            "id_solicitante": s.solicitante.id,
            "nombre": s.nombre,
            "extension": s.extension,
            "fecha_solicitud": iso(s.fecha_solicitud),
            "fecha_envio": iso(s.fecha_envio),
            "estado": s.estado.value,
        }

    @staticmethod
    def _escribir_insertar(d: dict[str, Any]) -> None:
        fila = SolicitudDominioOrm(
            solicitante_id=d["id_solicitante"],
            nombre=d["nombre"],
            extension=d["extension"],
            fecha_solicitud=a_fecha_hora(d["fecha_solicitud"]),
            fecha_envio=a_fecha_hora(d["fecha_envio"]),
            estado=d["estado"],
        )
        fila.save(force_insert=True)
        d["id"] = fila.id

    @staticmethod
    def _escribir_actualizar(d: dict[str, Any]) -> None:
        actualizado(
            SolicitudDominioOrm.objects.filter(id=d["id"]).update(
                nombre=d["nombre"],
                extension=d["extension"],
                fecha_envio=a_fecha_hora(d["fecha_envio"]),
                estado=d["estado"],
            ),
            "la solicitud de dominio",
            d["id"],
        )
