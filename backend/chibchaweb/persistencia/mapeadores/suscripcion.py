"""MapeadorSuscripcion: agregado Suscripcion con su sitio web y sus pagos."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import transaction
from django.db.models import Q

from chibchaweb.dominio.cuentas import Distribuidor
from chibchaweb.dominio.errores import NoEncontradoError, ValidacionError
from chibchaweb.dominio.facturacion import Pago
from chibchaweb.dominio.hospedaje import SitioWeb, Suscripcion
from chibchaweb.dominio.repositorios import RepositorioSuscripcion
from chibchaweb.dominio.respaldo import GestorContingencia
from chibchaweb.persistencia.mapeadores._cargador import RELACIONES_CLIENTE, Cargador
from chibchaweb.persistencia.mapeadores.base import (
    Mapeador,
    a_decimal,
    a_fecha,
    a_fecha_hora,
    a_json,
    actualizado,
    con_contingencia,
    de_json,
    iso,
    rango_de_fechas,
    traducir_fallas_de_lectura,
    traducir_restauracion,
    traducir_unico,
)
from chibchaweb.persistencia.modelos_orm import ClienteOrm, PagoOrm, SitioWebOrm, SuscripcionOrm


@traducir_fallas_de_lectura
class MapeadorSuscripcion(Mapeador[Suscripcion], RepositorioSuscripcion):
    """Respalda los cobros ejecutados ante una caída de la BD (RT04)."""

    def __init__(self, gestor: GestorContingencia):
        super().__init__("suscripcion")
        self._gestor = gestor

    @property
    def gestor(self) -> GestorContingencia:
        return self._gestor

    # --- Mapeador<Suscripcion> ------------------------------------------------------------------
    def insertar(self, objeto: Suscripcion) -> int:
        datos = self._a_datos(objeto, "insertar", con_pagos=True, con_ids=False)
        respaldo = a_json(datos)

        def accion() -> int:
            traducir_unico(lambda: self._escribir_insertar(datos))
            return datos["id"]

        id = con_contingencia(self._gestor, "Suscripcion.insertar", lambda: respaldo, accion)
        objeto.id = id
        if objeto.sitio.id is None:
            objeto.sitio.id = datos["sitio"]["id"]
        for pago, d in zip(objeto.pagos, datos["pagos"], strict=True):
            pago.id = d["id"]
        return id

    def actualizar(self, objeto: Suscripcion) -> None:
        """Actualiza la suscripción y su sitio. Los pagos nuevos se escriben con ``registrar_pago``."""
        if any(pago.id is None for pago in objeto.pagos):
            raise RuntimeError("actualizar no escribe los pagos nuevos: use registrar_pago(pago) para cada uno")
        datos = self._a_datos(objeto, "actualizar", con_pagos=False, con_ids=True)
        respaldo = a_json(datos)
        con_contingencia(
            self._gestor,
            "Suscripcion.actualizar",
            lambda: respaldo,
            lambda: traducir_unico(lambda: self._escribir_actualizar(datos)),
        )

    def buscar_por_id(self, id: int) -> Suscripcion:
        encontradas = self._cargar(SuscripcionOrm.objects.filter(id=id))
        if not encontradas:
            raise NoEncontradoError(f"No existe la suscripción {id}")
        return encontradas[0]

    def buscar_por_filtro(self, filtro: str) -> list[Suscripcion]:
        consulta = SuscripcionOrm.objects.all()
        texto = (filtro or "").strip()
        if texto:
            consulta = consulta.filter(
                Q(sitio__subdominio__icontains=texto)
                | Q(sitio__dominio_propio__icontains=texto)
                | Q(titular__usuario__nombre__icontains=texto)
                | Q(titular__usuario__correo__icontains=texto)
            )
        return self._cargar(consulta)

    # --- RepositorioSuscripcion -----------------------------------------------------------------
    def buscar_vencidas(self, fecha: date) -> list[Suscripcion]:
        return self._cargar(SuscripcionOrm.objects.filter(activa=True, fecha_corte__lte=fecha))

    def registrar_pago(self, pago: Pago) -> None:
        """Inserta un pago nuevo; si el pago ya tiene id (ya se escribió) no hace nada."""
        if pago.id is not None:
            return
        if pago.suscripcion.id is None:
            raise ValidacionError("suscripcion", "La suscripción del pago aún no se ha guardado")
        # Un cobro exitoso ya avanzó el corte en memoria: el evento lo lleva para que pago y corte se escriban
        # (y, en contingencia, se restauren) juntos y la sincronización no deje la suscripción cobrada y vencida.
        datos = {
            "_operacion": "registrar_pago",
            "pago": self._pago_a_datos(pago, False),
            "fecha_corte": iso(pago.suscripcion.fecha_corte) if pago.es_exitoso() else None,
        }
        respaldo = a_json(datos)

        def accion() -> None:
            self._escribir_pago(datos)

        con_contingencia(self._gestor, "Suscripcion.registrar_pago", lambda: respaldo, accion)
        pago.id = datos["pago"]["id"]

    def buscar_pagos_para_comision(self, distribuidor: Distribuidor, inicio: date, fin: date) -> list[Pago]:
        desde, hasta = rango_de_fechas(inicio, fin)
        filas = list(
            PagoOrm.objects.filter(
                estado="EXITOSO",
                comisionado=False,
                suscripcion__titular__distribuidor_id=distribuidor.id,
                fecha__gte=desde,
                fecha__lt=hasta,
            )
            .select_related("suscripcion")
            .order_by("fecha", "id")
        )
        cargador = Cargador(self._gestor)
        cargador.registrar_distribuidor(distribuidor)  # los clientes quedan ligados al mismo distribuidor
        self._clientes(cargador, {f.suscripcion.titular_id for f in filas})
        return [cargador.pago(f.id) for f in filas]

    def buscar_sitio(self, id: int) -> SitioWeb:
        fila = SitioWebOrm.objects.filter(id=id).first()
        if fila is None:
            raise NoEncontradoError(f"No existe el sitio {id}")
        return Cargador(self._gestor).sitio(fila)

    @traducir_restauracion
    def restaurar(self, contenido: str) -> None:
        """Reaplica el evento respaldado (insertar, actualizar o registrar un pago); no vuelve a respaldar."""
        datos = de_json(contenido)
        operacion = datos["_operacion"]
        with transaction.atomic():
            if operacion == "insertar":
                traducir_unico(lambda: self._escribir_insertar(datos))
            elif operacion == "actualizar":
                traducir_unico(lambda: self._escribir_actualizar(datos))
            else:
                self._escribir_pago(datos)

    # --- consultas ------------------------------------------------------------------------------
    def _cargar(self, consulta) -> list[Suscripcion]:
        filas = list(consulta.order_by("id").values_list("id", "titular_id"))
        cargador = Cargador(self._gestor)
        self._clientes(cargador, {titular for _, titular in filas})
        return [s for id, _ in filas if (s := cargador.suscripcion(id)) is not None]

    @staticmethod
    def _clientes(cargador: Cargador, ids_titulares: set[int]) -> None:
        """Carga los titulares con todas sus suscripciones y pagos (quedan en el mapa del cargador)."""
        if ids_titulares:
            cargador.clientes(
                ClienteOrm.objects.filter(usuario_id__in=ids_titulares).select_related(*RELACIONES_CLIENTE)
            )

    # --- dominio -> datos -----------------------------------------------------------------------
    def _a_datos(self, s: Suscripcion, operacion: str, con_pagos: bool, con_ids: bool) -> dict[str, Any]:
        if s.titular.id is None or s.paquete.id is None or s.plan.id is None:
            raise ValidacionError("suscripcion", "El titular, el paquete y el plan deben estar guardados")
        sitio = s.sitio
        datos: dict[str, Any] = {
            "_operacion": operacion,
            "id": s.id if con_ids else None,
            "id_titular": s.titular.id,
            "sitio": {
                "id": sitio.id if con_ids else None,
                "subdominio": sitio.subdominio,
                "dominio_propio": sitio.dominio_propio,
                "plataforma": sitio.plataforma.value,
            },
            "id_paquete": s.paquete.id,
            "id_plan": s.plan.id,
            "fecha_inicio": iso(s.fecha_inicio),
            "fecha_corte": iso(s.fecha_corte),
            "activa": s.activa,
        }
        if con_pagos:
            datos["pagos"] = [self._pago_a_datos(p, False) for p in s.pagos]
        return datos

    @staticmethod
    def _pago_a_datos(p: Pago, con_ids: bool) -> dict[str, Any]:
        return {
            "id": p.id if con_ids else None,
            "id_suscripcion": p.suscripcion.id,
            "monto": str(p.monto),
            "fecha": iso(p.fecha),
            "estado": p.estado.value,
            "referencia_franquicia": p.referencia_franquicia,
            "comisionado": p.comisionado,
        }

    # --- datos -> filas -------------------------------------------------------------------------
    def _escribir_insertar(self, d: dict[str, Any]) -> None:
        sitio = d["sitio"]
        fila_sitio = SitioWebOrm(
            subdominio=sitio["subdominio"], dominio_propio=sitio["dominio_propio"], plataforma=sitio["plataforma"]
        )
        fila_sitio.save(force_insert=True)
        sitio["id"] = fila_sitio.id
        fila = SuscripcionOrm(
            titular_id=d["id_titular"],
            sitio_id=fila_sitio.id,
            paquete_id=d["id_paquete"],
            plan_id=d["id_plan"],
            fecha_inicio=a_fecha(d["fecha_inicio"]),
            fecha_corte=a_fecha(d["fecha_corte"]),
            activa=d["activa"],
        )
        fila.save(force_insert=True)
        d["id"] = fila.id
        for pago in d.get("pagos", []):
            pago["id_suscripcion"] = fila.id
            self._insertar_pago(pago)

    @staticmethod
    def _escribir_actualizar(d: dict[str, Any]) -> None:
        sitio = d["sitio"]
        actualizado(
            SuscripcionOrm.objects.filter(id=d["id"]).update(
                paquete_id=d["id_paquete"],
                plan_id=d["id_plan"],
                fecha_corte=a_fecha(d["fecha_corte"]),
                activa=d["activa"],
            ),
            "la suscripción",
            d["id"],
        )
        SitioWebOrm.objects.filter(suscripcion__id=d["id"]).update(
            subdominio=sitio["subdominio"], dominio_propio=sitio["dominio_propio"], plataforma=sitio["plataforma"]
        )

    def _escribir_pago(self, d: dict[str, Any]) -> None:
        """Inserta el pago y, si era exitoso, deja la fecha de corte de la suscripción donde quedó tras cobrar."""
        self._insertar_pago(d["pago"])
        if d.get("fecha_corte"):
            SuscripcionOrm.objects.filter(id=d["pago"]["id_suscripcion"]).update(fecha_corte=a_fecha(d["fecha_corte"]))

    @staticmethod
    def _insertar_pago(p: dict[str, Any]) -> None:
        fila = PagoOrm(
            suscripcion_id=p["id_suscripcion"],
            monto=a_decimal(p["monto"]),
            fecha=a_fecha_hora(p["fecha"]),
            estado=p["estado"],
            referencia_franquicia=p["referencia_franquicia"],
            comisionado=p["comisionado"],
        )
        fila.save(force_insert=True)
        p["id"] = fila.id
