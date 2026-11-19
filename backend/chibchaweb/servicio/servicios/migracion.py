"""Migración (MIG): datos legados en dos fases con punto de control manual (CU-MIG-01)."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from chibchaweb.dominio.cuentas import Cliente, Empleado
from chibchaweb.dominio.errores import ContingenciaActivaError, ErrorDominio, ReglaNegocioError
from chibchaweb.dominio.hospedaje import Suscripcion
from chibchaweb.dominio.integraciones import FuenteLegada
from chibchaweb.dominio.migracion import (
    ClienteLegado,
    CreadorRegistroLegado,
    EntradaLog,
    EstadoMigracion,
    HostingLegado,
    NivelLog,
    PagoLegado,
    ProcesoMigracion,
)
from chibchaweb.dominio.repositorios import (
    RepositorioCatalogo,
    RepositorioMigracion,
    RepositorioSuscripcion,
    RepositorioUsuario,
    UnidadDeTrabajo,
)
from chibchaweb.servicio.dto import ResultadoMigracionDTO
from chibchaweb.servicio.servicios._comun import _exigir_activo

_registro = logging.getLogger(__name__)


class ServicioMigracion:
    """Migración de datos legados en dos fases (módulo MIG). Abre la transacción de la ejecución real."""

    def __init__(
        self,
        fuente: FuenteLegada,
        creadores: Sequence[CreadorRegistroLegado],
        migraciones: RepositorioMigracion,
        usuarios: RepositorioUsuario,
        suscripciones: RepositorioSuscripcion,
        catalogo: RepositorioCatalogo,
        unidad_trabajo: UnidadDeTrabajo,
    ):
        self._fuente = fuente
        self._creadores = creadores  # perezosa en el contenedor: no se copia a una lista
        self._migraciones = migraciones
        self._usuarios = usuarios
        self._suscripciones = suscripciones
        self._catalogo = catalogo
        self._unidad_trabajo = unidad_trabajo

    # --- fase 1: simulación -----------------------------------------------------------------------
    def migrar_registros_legados(self, id_ejecutor: int) -> ResultadoMigracionDTO:
        """CU-MIG-01, fase 1 (RN-26). Simula la migración sin escribir datos de negocio y guarda el proceso
        ``SIMULADA`` con su log. Solo un empleado activo puede ejecutarla."""
        ejecutor = self._usuarios.buscar_por_id(id_ejecutor)
        if not isinstance(ejecutor, Empleado):
            raise ReglaNegocioError("Solo un empleado puede ejecutar una migración")
        _exigir_activo(ejecutor)
        proceso = ProcesoMigracion(ejecutor, list(self._creadores))
        proceso.simular(self._fuente)
        id_proceso = self._migraciones.insertar(proceso)
        return ResultadoMigracionDTO(
            id_proceso,
            proceso.cantidad_validos(),
            proceso.cantidad_invalidos(),
            tuple(_linea_de_log(e) for e in proceso.log),
        )

    # --- fase 2: ejecución real -------------------------------------------------------------------
    def confirmar_migracion(self, id_proceso: int) -> EstadoMigracion:
        """CU-MIG-01, fase 2 (RN-25, RN-27, RN-28). Aprueba, comprueba que la fuente no cambió y escribe solo los
        registros válidos (clientes → suscripciones → pagos) en una unidad de trabajo todo o nada.

        Devuelve ``EJECUTADA``; si cualquier escritura falla se revierte todo y el proceso queda ``REVERTIDA``
        (eso sí se guarda, después de revertir). Una transición no permitida es ``EstadoInvalidoError`` y una
        fuente distinta a la simulada es ``ReglaNegocioError``; en ambos casos no se escribe nada.
        """
        proceso = self._migraciones.buscar_por_id(id_proceso)
        proceso.aprobar()
        proceso.preparar_ejecucion(self._fuente)
        self._unidad_trabajo.iniciar()
        try:
            resumen = self._escribir(proceso)
            proceso.agregar_entrada(EntradaLog(NivelLog.INFO, f"Migración ejecutada: {resumen}"))
            proceso.marcar_ejecutado()
            self._migraciones.actualizar(proceso)
        except ContingenciaActivaError:
            self._revertir()  # la BD cayó: no se puede dejar constancia en ella; se avisa con 503
            raise
        except Exception as exc:
            self._revertir()
            return self._registrar_reversion(id_proceso, exc)
        self._unidad_trabajo.confirmar()
        return proceso.estado

    def cancelar_migracion(self, id_proceso: int) -> None:
        """CU-MIG-01 (RN-25). Solo un proceso ``CREADA`` o ``SIMULADA`` se puede cancelar."""
        proceso = self._migraciones.buscar_por_id(id_proceso)
        proceso.cancelar()
        self._migraciones.actualizar(proceso)

    # --- auxiliares -------------------------------------------------------------------------------
    def _escribir(self, proceso: ProcesoMigracion) -> str:
        """Escribe los registros válidos en el orden clientes → suscripciones → pagos (RN-27).

        Las suscripciones migradas nacen con ``fecha_inicio = fecha_corte = hoy`` (RN-04, ver decisiones D-31):
        el primer cobro lo hace la tarea programada que corra desde el día siguiente.
        """
        validos = [r for r in proceso.registros if r.valido]
        paquetes = {p.nombre: p for p in self._catalogo.listar_paquetes()}
        planes = {p.nombre: p for p in self._catalogo.listar_planes()}
        clientes: dict[str, Cliente] = {}
        suscripciones: dict[str, Suscripcion] = {}  # por identificador legado del cliente
        pagos = 0
        for registro in validos:
            if isinstance(registro, ClienteLegado):
                cliente = registro.a_cliente()  # RN-28: sin cuenta de acceso; tarjeta sin validador externo
                self._usuarios.insertar(cliente)
                clientes[registro.identificador_legado] = cliente
        for registro in validos:
            if isinstance(registro, HostingLegado):
                suscripcion = registro.a_suscripcion(
                    clientes[registro.identificador_cliente], paquetes[registro.paquete], planes[registro.plan]
                )
                self._suscripciones.insertar(suscripcion)
                suscripciones.setdefault(registro.identificador_cliente, suscripcion)
        for registro in validos:
            if isinstance(registro, PagoLegado):
                pago = registro.a_pago(suscripciones[registro.identificador_cliente])
                self._suscripciones.registrar_pago(pago)
                pagos += 1
        total_suscripciones = sum(len(c.suscripciones) for c in clientes.values())
        return f"{len(clientes)} clientes, {total_suscripciones} suscripciones y {pagos} pagos"

    def _revertir(self) -> None:
        try:
            self._unidad_trabajo.revertir()
        except Exception:  # la conexión puede estar rota: no debe tapar el error original
            _registro.exception("No se pudo revertir la unidad de trabajo de la migración")

    def _registrar_reversion(self, id_proceso: int, causa: Exception) -> EstadoMigracion:
        """Guarda ``REVERTIDA`` (ya fuera de la unidad de trabajo, tras revertir; RN-27)."""
        motivo = causa.mensaje if isinstance(causa, ErrorDominio) else type(causa).__name__
        proceso = self._migraciones.buscar_por_id(id_proceso)  # en la BD el estado sigue siendo SIMULADA
        if proceso.estado is EstadoMigracion.SIMULADA:  # RN-25: SIMULADA -> APROBADA -> REVERTIDA
            proceso.aprobar()
        proceso.agregar_entrada(EntradaLog(NivelLog.ERROR, f"Migración revertida: {motivo}"))
        proceso.marcar_revertido()
        self._migraciones.actualizar(proceso)
        return proceso.estado


def _linea_de_log(entrada: EntradaLog) -> str:
    """``NIVEL|tipo|idLegado|mensaje`` (api.md). El mensaje va al final y sin saltos de línea."""
    mensaje = " ".join(entrada.mensaje.split())
    return f"{entrada.nivel.value}|{entrada.tipo_registro or ''}|{entrada.identificador_legado or ''}|{mensaje}"
