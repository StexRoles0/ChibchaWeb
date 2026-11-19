"""MapeadorComision: agregado Comision con su cheque (marca ``pago.id_comision`` de los pagos base)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q

from chibchaweb.dominio.errores import NoEncontradoError, ValidacionError
from chibchaweb.dominio.facturacion import Cheque, Comision
from chibchaweb.dominio.repositorios import RepositorioComision
from chibchaweb.dominio.respaldo import GestorContingencia
from chibchaweb.persistencia.mapeadores._cargador import RELACIONES_CLIENTE, Cargador
from chibchaweb.persistencia.mapeadores.base import (
    Mapeador,
    a_decimal,
    a_fecha,
    a_json,
    actualizado,
    con_contingencia,
    de_json,
    iso,
    traducir_fallas_de_lectura,
    traducir_restauracion,
    traducir_unico,
)
from chibchaweb.persistencia.modelos_orm import ChequeOrm, ClienteOrm, ComisionOrm, PagoOrm


@traducir_fallas_de_lectura
class MapeadorComision(Mapeador[Comision], RepositorioComision):
    """Respalda los cheques emitidos ante una caída de la BD (RT04)."""

    def __init__(self, gestor: GestorContingencia):
        super().__init__("comision")
        self._gestor = gestor

    @property
    def gestor(self) -> GestorContingencia:
        return self._gestor

    # --- Mapeador<Comision> ---------------------------------------------------------------------
    def insertar(self, objeto: Comision) -> int:
        datos = self._a_datos(objeto, "insertar", con_ids=False)
        respaldo = a_json(datos)

        def accion() -> int:
            traducir_unico(lambda: self._escribir_insertar(datos))
            return datos["id"]

        id = con_contingencia(self._gestor, "Comision.insertar", lambda: respaldo, accion)
        objeto.id = id
        if objeto.cheque is not None and objeto.cheque.id is None:
            objeto.cheque.id = datos["cheque"]["id"]
        return id

    def actualizar(self, objeto: Comision) -> None:
        """Actualiza la comisión y marca sus pagos base. El cheque se escribe con ``registrar_cheque``."""
        if objeto.cheque is not None and objeto.cheque.id is None:
            raise RuntimeError("actualizar no escribe el cheque nuevo: use registrar_cheque(comision) antes")
        datos = self._a_datos(objeto, "actualizar", con_ids=True)
        datos.pop("cheque")
        respaldo = a_json(datos)
        con_contingencia(
            self._gestor,
            "Comision.actualizar",
            lambda: respaldo,
            lambda: traducir_unico(lambda: self._escribir_actualizar(datos)),
        )

    def buscar_por_id(self, id: int) -> Comision:
        encontradas = self._cargar(ComisionOrm.objects.filter(id=id))
        if not encontradas:
            raise NoEncontradoError(f"No existe la comisión {id}")
        return encontradas[0]

    def buscar_por_filtro(self, filtro: str) -> list[Comision]:
        consulta = ComisionOrm.objects.all()
        texto = (filtro or "").strip()
        if texto:
            consulta = consulta.filter(
                Q(beneficiario__usuario__nombre__icontains=texto)
                | Q(beneficiario__usuario__correo__icontains=texto)
                | Q(beneficiario__codigo__icontains=texto)
                | Q(nombre_categoria__icontains=texto)
                | Q(cheque__numero__icontains=texto)
            )
        return self._cargar(consulta)

    # --- RepositorioComision --------------------------------------------------------------------
    def registrar_cheque(self, comision: Comision) -> None:
        """Inserta el cheque de la comisión; si ya tiene id (ya se escribió) no hace nada."""
        cheque = comision.cheque
        if cheque is None:
            raise ValidacionError("cheque", "La comisión no tiene cheque que registrar")
        if cheque.id is not None:
            return
        if comision.id is None:
            raise ValidacionError("comision", "La comisión aún no se ha guardado")
        datos = {"_operacion": "registrar_cheque", "cheque": self._cheque_a_datos(cheque, comision.id)}
        respaldo = a_json(datos)

        def accion() -> None:
            traducir_unico(lambda: self._insertar_cheque(datos["cheque"]))

        con_contingencia(self._gestor, "Comision.registrar_cheque", lambda: respaldo, accion)
        cheque.id = datos["cheque"]["id"]

    @traducir_restauracion
    def restaurar(self, contenido: str) -> None:
        """Reaplica el evento respaldado (insertar, actualizar o registrar cheque); no vuelve a respaldar."""
        datos = de_json(contenido)
        operacion = datos["_operacion"]
        with transaction.atomic():
            if operacion == "insertar":
                traducir_unico(lambda: self._escribir_insertar(datos))
            elif operacion == "actualizar":
                traducir_unico(lambda: self._escribir_actualizar(datos))
            else:
                traducir_unico(lambda: self._insertar_cheque(datos["cheque"]))

    # --- consultas ------------------------------------------------------------------------------
    def _cargar(self, consulta) -> list[Comision]:
        filas = list(consulta.select_related("beneficiario__usuario", "cheque").order_by("id"))
        cargador = Cargador(self._gestor)
        pagos = list(PagoOrm.objects.filter(comision_id__in=[f.id for f in filas]).select_related("suscripcion"))
        titulares = {p.suscripcion.titular_id for p in pagos}
        if titulares:  # los pagos base cuelgan de las suscripciones de sus titulares
            cargador.clientes(ClienteOrm.objects.filter(usuario_id__in=titulares).select_related(*RELACIONES_CLIENTE))
        base: dict[int, list] = {}
        for p in sorted(pagos, key=lambda p: p.id):
            base.setdefault(p.comision_id, []).append(cargador.pago(p.id))
        resultado = []
        for f in filas:
            try:
                c = f.cheque
                cheque = Cheque(c.numero, c.beneficiario, c.monto, c.fecha_emision, id=c.id)
            except ObjectDoesNotExist:
                cheque = None
            resultado.append(
                Comision(
                    f.fecha_inicio,
                    f.fecha_fin,
                    f.clientes_referidos,
                    f.nombre_categoria,
                    f.porcentaje,
                    cargador.distribuidor(f.beneficiario),
                    id=f.id,
                    pagos_base=base.get(f.id, []),
                    cheque=cheque,
                )
            )
        return resultado

    # --- dominio -> datos -----------------------------------------------------------------------
    def _a_datos(self, c: Comision, operacion: str, con_ids: bool) -> dict[str, Any]:
        if c.beneficiario.id is None or any(p.id is None for p in c.pagos_base):
            raise ValidacionError("comision", "El beneficiario y los pagos base deben estar guardados")
        return {
            "_operacion": operacion,
            "id": c.id if con_ids else None,
            "id_beneficiario": c.beneficiario.id,
            "fecha_inicio": iso(c.fecha_inicio),
            "fecha_fin": iso(c.fecha_fin),
            "clientes_referidos": c.clientes_referidos,
            "nombre_categoria": c.nombre_categoria,
            "porcentaje": str(c.porcentaje),
            "ids_pagos_base": [p.id for p in c.pagos_base],
            "cheque": self._cheque_a_datos(c.cheque, c.id if con_ids else None) if c.cheque is not None else None,
        }

    @staticmethod
    def _cheque_a_datos(ch: Cheque, id_comision: int | None) -> dict[str, Any]:
        return {
            "id": None,
            "id_comision": id_comision,
            "numero": ch.numero,
            "beneficiario": ch.beneficiario,
            "monto": str(ch.monto),
            "fecha_emision": iso(ch.fecha_emision),
        }

    # --- datos -> filas -------------------------------------------------------------------------
    def _escribir_insertar(self, d: dict[str, Any]) -> None:
        fila = ComisionOrm(
            beneficiario_id=d["id_beneficiario"],
            fecha_inicio=a_fecha(d["fecha_inicio"]),
            fecha_fin=a_fecha(d["fecha_fin"]),
            clientes_referidos=d["clientes_referidos"],
            nombre_categoria=d["nombre_categoria"],
            porcentaje=a_decimal(d["porcentaje"]),
        )
        fila.save(force_insert=True)
        d["id"] = fila.id
        self._marcar_pagos(fila.id, d["ids_pagos_base"])
        if d.get("cheque") is not None:
            d["cheque"]["id_comision"] = fila.id
            self._insertar_cheque(d["cheque"])

    def _escribir_actualizar(self, d: dict[str, Any]) -> None:
        actualizado(
            ComisionOrm.objects.filter(id=d["id"]).update(
                beneficiario_id=d["id_beneficiario"],
                fecha_inicio=a_fecha(d["fecha_inicio"]),
                fecha_fin=a_fecha(d["fecha_fin"]),
                clientes_referidos=d["clientes_referidos"],
                nombre_categoria=d["nombre_categoria"],
                porcentaje=a_decimal(d["porcentaje"]),
            ),
            "la comisión",
            d["id"],
        )
        self._marcar_pagos(d["id"], d["ids_pagos_base"])

    @staticmethod
    def _marcar_pagos(id_comision: int, ids_pagos: list[int]) -> None:
        if ids_pagos:
            PagoOrm.objects.filter(id__in=ids_pagos).update(comisionado=True, comision_id=id_comision)

    @staticmethod
    def _insertar_cheque(c: dict[str, Any]) -> None:
        fila = ChequeOrm(
            comision_id=c["id_comision"],
            numero=c["numero"],
            beneficiario=c["beneficiario"],
            monto=a_decimal(c["monto"]),
            fecha_emision=a_fecha(c["fecha_emision"]),
        )
        fila.save(force_insert=True)
        c["id"] = fila.id
