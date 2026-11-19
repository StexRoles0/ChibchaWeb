"""Comisiones (COM): liquidación por periodo y emisión de cheques (CU-COM-01, CU-COM-02)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from chibchaweb.dominio.errores import ValidacionError
from chibchaweb.dominio.facturacion import CategoriaDistribuidor, Cheque, Comision
from chibchaweb.dominio.repositorios import RepositorioComision, RepositorioSuscripcion, RepositorioUsuario
from chibchaweb.servicio._tiempo import hoy
from chibchaweb.servicio.dto import ResumenDTO

_MAXIMO_BENEFICIARIO = 120  # Cheque.beneficiario


class ServicioComisiones:
    """Liquidación de comisiones y emisión de cheques (módulo COM). Lo dispara el programador de tareas."""

    def __init__(
        self,
        categorias: Sequence[CategoriaDistribuidor],
        comisiones: RepositorioComision,
        usuarios: RepositorioUsuario,
        suscripciones: RepositorioSuscripcion,
    ):
        if not categorias:
            raise ValidacionError("categorias", "Se necesita al menos una categoría de distribuidor")
        self._categorias = list(categorias)
        self._comisiones = comisiones
        self._usuarios = usuarios
        self._suscripciones = suscripciones

    def calcular_comision(self, fecha_inicio: date, fecha_fin: date) -> int:
        """CU-COM-01 (RN-19, RN-20). Crea una ``Comision`` por cada distribuidor con pagos EXITOSO sin comisionar de
        sus referidos dentro de [inicio, fin] y devuelve cuántas creó.

        La categoría y el porcentaje salen de ``Distribuidor.determinar_categoria`` (el distribuidor se carga con sus
        referidos). Cada pago base queda ``comisionado``; volver a correr el mismo periodo no crea nada nuevo.
        Si la BD cae (``ContingenciaActivaError``) el cálculo se detiene.
        """
        if not isinstance(fecha_inicio, date) or not isinstance(fecha_fin, date):
            raise ValidacionError("fechaInicio", "El periodo de la comisión es obligatorio")
        if fecha_fin < fecha_inicio:
            raise ValidacionError("fechaFin", "La fecha fin no puede ser anterior a la de inicio")
        creadas = 0
        for distribuidor in self._usuarios.buscar_distribuidores(""):
            pagos = self._suscripciones.buscar_pagos_para_comision(distribuidor, fecha_inicio, fecha_fin)
            if not pagos:  # RN-20: sin pagos no hay comisión
                continue
            categoria = distribuidor.determinar_categoria(self._categorias)
            comision = Comision(
                fecha_inicio,
                fecha_fin,
                distribuidor.cantidad_referidos(),
                categoria.nombre(),
                categoria.porcentaje(),
                distribuidor,
            )
            for pago in pagos:
                comision.agregar_pago_base(pago)
            self._comisiones.insertar(comision)
            distribuidor.agregar_comision(comision)
            creadas += 1
        return creadas

    def generar_cheque(self, id_comision: int) -> None:
        """CU-COM-02 (RN-21). Emite el cheque de la comisión: ``CHQ-<año>-<id de 6 dígitos>`` a nombre y documento del
        distribuidor, por el monto de la comisión. Falla (``ReglaNegocioError``) si ya tiene cheque."""
        comision = self._comisiones.buscar_por_id(id_comision)
        emision = hoy()
        distribuidor = comision.beneficiario
        documento = getattr(distribuidor, "documento", "")
        sufijo = f" - {documento}"
        beneficiario = f"{distribuidor.nombre[: _MAXIMO_BENEFICIARIO - len(sufijo)]}{sufijo}"
        cheque = Cheque(f"CHQ-{emision.year}-{comision.id:06d}", beneficiario, comision.calcular_monto(), emision)
        comision.asociar_cheque(cheque)  # RN-21: el dominio rechaza una comisión que ya tiene cheque
        self._comisiones.registrar_cheque(comision)

    def consultar_comisiones_sin_cheque(self) -> list[ResumenDTO]:
        """P-08. Comisiones aún sin cheque (insumo de la tarea ``generar_cheques``)."""
        return [
            ResumenDTO(
                c.id,  # type: ignore[arg-type]
                f"{c.beneficiario.nombre} ({c.nombre_categoria})",
                f"{c.fecha_inicio.isoformat()} a {c.fecha_fin.isoformat()} · {c.calcular_monto()}",
                "SIN_CHEQUE",
            )
            for c in self._comisiones.buscar_por_filtro("")
            if not c.tiene_cheque()
        ]
