"""Migración (DC-MDO-01): proceso en dos fases con punto de control manual y su log."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from chibchaweb.dominio._comun import ahora, propiedad_id, texto_obligatorio
from chibchaweb.dominio.errores import EstadoInvalidoError, ReglaNegocioError, ValidacionError
from chibchaweb.dominio.migracion.registros import (
    ClienteLegado,
    CreadorRegistroLegado,
    HostingLegado,
    PagoLegado,
    RegistroLegado,
)

if TYPE_CHECKING:
    from chibchaweb.dominio.cuentas import Empleado
    from chibchaweb.dominio.integraciones import FuenteLegada


class EstadoMigracion(enum.Enum):
    """Estados del proceso de migración (RN-25)."""

    CREADA = "CREADA"
    SIMULADA = "SIMULADA"
    APROBADA = "APROBADA"
    EJECUTADA = "EJECUTADA"
    REVERTIDA = "REVERTIDA"
    CANCELADA = "CANCELADA"


class NivelLog(enum.Enum):
    """Severidad de una entrada del log."""

    INFO = "INFO"
    ADVERTENCIA = "ADVERTENCIA"
    ERROR = "ERROR"


class EntradaLog:
    """Línea del log de una migración."""

    id = propiedad_id()

    def __init__(
        self,
        nivel: NivelLog,
        mensaje: str,
        id: int | None = None,
        fecha: datetime | None = None,
        identificador_legado: str | None = None,
        tipo_registro: str | None = None,
    ):
        if not isinstance(nivel, NivelLog):
            raise ValidacionError("nivel", "Nivel de log inválido")
        self._id = id
        self._fecha = fecha or ahora()
        self._nivel = nivel
        self._mensaje = texto_obligatorio(mensaje, "mensaje", 4000)
        self._identificador_legado = (identificador_legado or "")[:50] or None
        if tipo_registro is not None and tipo_registro not in ("CLIENTE", "HOSTING", "PAGO"):
            raise ValidacionError("tipoRegistro", "Tipo de registro legado inválido")
        self._tipo_registro = tipo_registro

    @property
    def fecha(self) -> datetime:
        return self._fecha

    @property
    def nivel(self) -> NivelLog:
        return self._nivel

    @property
    def mensaje(self) -> str:
        return self._mensaje

    @property
    def identificador_legado(self) -> str | None:
        return self._identificador_legado

    @property
    def tipo_registro(self) -> str | None:
        return self._tipo_registro

    def es_error(self) -> bool:
        return self._nivel is NivelLog.ERROR

    def __repr__(self) -> str:
        return f"EntradaLog({self._nivel.value}, {self._tipo_registro}, {self._identificador_legado!r})"


# --------------------------------------------------------------------------------------------------
# Proceso de migración
# --------------------------------------------------------------------------------------------------


class ProcesoMigracion:
    """Migración en dos fases (simulación y ejecución real) con punto de control manual."""

    id = propiedad_id()

    def __init__(
        self,
        ejecutor: Empleado,
        creadores: list[CreadorRegistroLegado],
        id: int | None = None,
        fecha_inicio: datetime | None = None,
        fecha_fin: datetime | None = None,
        estado: EstadoMigracion = EstadoMigracion.CREADA,
        log: list[EntradaLog] | None = None,
    ):
        if ejecutor is None:
            raise ValidacionError("ejecutor", "El proceso necesita un ejecutor")
        if not creadores:
            raise ValidacionError("creadores", "Se necesita al menos un creador de registros")
        tipos = [c.tipo() for c in creadores]
        if len(set(tipos)) != len(tipos):
            raise ValidacionError("creadores", "Hay dos creadores para el mismo tipo de registro")
        if not isinstance(estado, EstadoMigracion):
            raise ValidacionError("estado", "Estado de migración inválido")
        self._id = id
        self._fecha_inicio = fecha_inicio or ahora()
        self._fecha_fin = fecha_fin
        self._estado = estado
        self._ejecutor = ejecutor
        self._registros: list[RegistroLegado] = []
        self._log: list[EntradaLog] = list(log or [])
        self._creadores: list[CreadorRegistroLegado] = list(creadores)

    @property
    def fecha_inicio(self) -> datetime:
        return self._fecha_inicio

    @property
    def fecha_fin(self) -> datetime | None:
        return self._fecha_fin

    @property
    def estado(self) -> EstadoMigracion:
        return self._estado

    @property
    def ejecutor(self) -> Empleado:
        return self._ejecutor

    @property
    def registros(self) -> tuple[RegistroLegado, ...]:
        return tuple(self._registros)

    @property
    def log(self) -> tuple[EntradaLog, ...]:
        return tuple(self._log)

    @property
    def creadores(self) -> tuple[CreadorRegistroLegado, ...]:
        return tuple(self._creadores)

    def simular(self, fuente: FuenteLegada) -> None:
        """RN-26: crea y valida cada registro, y escribe INFO o ERROR en el log sin escribir datos."""
        self._exigir_estado(EstadoMigracion.CREADA)
        desconocidos = self._leer(fuente)
        for registro in self._registros:
            tipo = self._tipo_de(registro)
            if registro.valido:
                entrada = EntradaLog(NivelLog.INFO, "Registro válido", None, None, registro.identificador_legado, tipo)
            else:
                mensaje = registro.describir_errores() or "Registro inválido"
                entrada = EntradaLog(NivelLog.ERROR, mensaje, None, None, registro.identificador_legado, tipo)
            self.agregar_entrada(entrada)
        for linea in desconocidos:
            self.agregar_entrada(EntradaLog(NivelLog.ERROR, f"Registro sin tipo reconocido: {linea[:200]}"))
        self._estado = EstadoMigracion.SIMULADA

    def agregar_entrada(self, entrada: EntradaLog) -> None:
        self._log.append(entrada)

    def cantidad_validos(self) -> int:
        return sum(1 for r in self._registros if r.valido)

    def cantidad_invalidos(self) -> int:
        return sum(1 for r in self._registros if not r.valido)

    def aprobar(self) -> None:
        self._exigir_estado(EstadoMigracion.SIMULADA)
        self._estado = EstadoMigracion.APROBADA

    def cancelar(self) -> None:
        self._exigir_estado(EstadoMigracion.CREADA, EstadoMigracion.SIMULADA)
        self._estado = EstadoMigracion.CANCELADA
        self._fecha_fin = ahora()

    def puede_ejecutarse(self) -> bool:
        return self._estado is EstadoMigracion.APROBADA

    def marcar_ejecutado(self) -> None:
        self._exigir_estado(EstadoMigracion.APROBADA)
        self._estado = EstadoMigracion.EJECUTADA
        self._fecha_fin = ahora()

    def marcar_revertido(self) -> None:
        self._exigir_estado(EstadoMigracion.APROBADA)
        self._estado = EstadoMigracion.REVERTIDA
        self._fecha_fin = ahora()

    def preparar_ejecucion(self, fuente: FuenteLegada) -> None:
        """RN-27: vuelve a leer sin escribir en el log y exige los mismos válidos que la simulación."""
        if not self.puede_ejecutarse():
            raise EstadoInvalidoError("El proceso debe estar APROBADO para ejecutarse")
        self._leer(fuente)
        validos_simulacion = sum(1 for e in self._log if e.nivel is NivelLog.INFO and e.tipo_registro is not None)
        if self.cantidad_validos() != validos_simulacion:
            raise ReglaNegocioError("La fuente cambió desde la simulación")

    # --- auxiliares ---------------------------------------------------------------------------
    def _exigir_estado(self, *permitidos: EstadoMigracion) -> None:
        """RN-25: cualquier transición no permitida lanza EstadoInvalidoError."""
        if self._estado not in permitidos:
            raise EstadoInvalidoError(f"Transición no permitida desde {self._estado.value}")

    def _tipo_de(self, registro: RegistroLegado) -> str | None:
        return {ClienteLegado: "CLIENTE", HostingLegado: "HOSTING", PagoLegado: "PAGO"}.get(type(registro))

    def _leer(self, fuente: FuenteLegada) -> list[str]:
        """Crea los registros con el creador de su tipo y verifica las referencias entre ellos."""
        por_tipo = {c.tipo(): c for c in self._creadores}
        self._registros = []
        desconocidos: list[str] = []
        for linea in fuente.leer_registros():
            tipo, separador, datos = (linea or "").partition("|")
            creador = por_tipo.get(tipo.strip().upper())
            if not separador or creador is None:
                desconocidos.append(linea or "")
                continue
            self._registros.append(creador.procesar(datos))
        self._verificar_referencias()
        return desconocidos

    def _verificar_referencias(self) -> None:
        """Clientes únicos; hosting y pagos de clientes válidos; subdominios únicos; pagos con hosting."""
        clientes: set[str] = set()
        correos: set[str] = set()
        for r in self._registros:
            if isinstance(r, ClienteLegado) and r.valido:
                if r.identificador_legado in clientes:
                    r._invalidar("Identificador de cliente repetido")
                elif r.correo in correos:
                    r._invalidar("Correo repetido")
                else:
                    clientes.add(r.identificador_legado)
                    correos.add(r.correo)
        con_hosting: set[str] = set()
        subdominios: set[str] = set()
        for r in self._registros:
            if isinstance(r, HostingLegado) and r.valido:
                if r.identificador_cliente not in clientes:
                    r._invalidar(f"El cliente {r.identificador_cliente} no existe entre los clientes migrados")
                elif r.subdominio in subdominios:
                    r._invalidar("Subdominio repetido")
                else:
                    subdominios.add(r.subdominio)
                    con_hosting.add(r.identificador_cliente)
        for r in self._registros:
            if isinstance(r, PagoLegado) and r.valido:
                if r.identificador_cliente not in clientes:
                    r._invalidar(f"El cliente {r.identificador_cliente} no existe entre los clientes migrados")
                elif r.identificador_cliente not in con_hosting:
                    r._invalidar("El cliente no tiene un hospedaje válido al que asociar el pago")

    def __repr__(self) -> str:
        return f"ProcesoMigracion(id={self._id!r}, estado={self._estado.value})"
