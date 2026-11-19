"""Contingencia (RT04): respaldo cifrado, sincronización y algoritmo de cifrado en ejecución."""

from __future__ import annotations

import logging

from chibchaweb.dominio.errores import ContingenciaActivaError, ErrorDominio, ReglaNegocioError
from chibchaweb.dominio.repositorios import (
    RepositorioComision,
    RepositorioSolicitudDominio,
    RepositorioSuscripcion,
    RepositorioUsuario,
    UnidadDeTrabajo,
)
from chibchaweb.dominio.respaldo import GestorContingencia
from chibchaweb.servicio.dto import ResumenDTO

_registro = logging.getLogger(__name__)


class ServicioContingencia:
    """Sincronización del respaldo y cambio de algoritmo de cifrado (RT04)."""

    def __init__(
        self,
        gestor: GestorContingencia,
        usuarios: RepositorioUsuario,
        suscripciones: RepositorioSuscripcion,
        comisiones: RepositorioComision,
        solicitudes: RepositorioSolicitudDominio,
        unidad_trabajo: UnidadDeTrabajo,
    ):
        self._gestor = gestor
        self._usuarios = usuarios
        self._suscripciones = suscripciones
        self._comisiones = comisiones
        self._solicitudes = solicitudes
        self._unidad_trabajo = unidad_trabajo  # P-22, D-27: sincronización todo o nada

    def consultar_respaldo_pendiente(self) -> list[ResumenDTO]:
        """P-06. Eventos pendientes del respaldo, en el orden en que se escribieron (M-20).

        Solo trae el tipo de evento y el algoritmo con que se cifró, que están en claro en cada línea del medio.
        **No** descifra nada: el contenido de un evento puede traer datos de tarjeta. Por eso tampoco necesita la BD
        y funciona durante la contingencia.
        """
        resumenes = []
        for posicion, linea in enumerate(self._gestor.medio.leer_pendientes(), start=1):
            algoritmo, separador, resto = linea.partition("|")
            tipo, _, _ = resto.partition("|")
            if separador and tipo:
                resumenes.append(ResumenDTO(posicion, tipo, algoritmo, "PENDIENTE"))
            else:
                resumenes.append(ResumenDTO(posicion, "(formato inválido)", "", "INVALIDO"))
        return resumenes

    def sincronizar_respaldo(self) -> int:
        """RT04 (RN-30, D-27). Reinserta los eventos pendientes, en orden, y devuelve cuántos reinsertó.

        Todo ocurre dentro de una ``UnidadDeTrabajo``: si un evento falla se revierte lo ya aplicado, **no** se
        vacía el medio y el error dice cuántos de cuántos se habían procesado (reintentar no duplica filas). Solo si
        todos entran se confirma y se llama ``confirmar_sincronizacion()``. Con la BD caída falla la propia unidad
        de trabajo y el respaldo queda intacto.
        """
        pendientes = self._gestor.recuperar_pendientes()
        total = len(pendientes)
        if total == 0:
            return 0
        self._unidad_trabajo.iniciar()
        procesados = 0
        tipo = ""
        try:
            for evento in pendientes:
                tipo, _, contenido = evento.partition("|")  # P-14: "<tipoEvento>|<contenido>"
                self._repositorio_de(tipo).restaurar(contenido)
                procesados += 1
        except ContingenciaActivaError:  # la BD sigue caída: 503, el respaldo queda intacto
            self._revertir()
            raise
        except ErrorDominio as exc:
            self._revertir()
            raise ReglaNegocioError(
                f"La sincronización se detuvo en el evento {procesados + 1} de {total} ({tipo}): {exc.mensaje} "
                f"Se procesaron {procesados} de {total} antes del fallo; se revirtió todo y el respaldo se conserva."
            ) from exc
        except Exception:
            self._revertir()
            raise
        self._unidad_trabajo.confirmar()
        self._gestor.confirmar_sincronizacion()
        return total

    def cambiar_algoritmo_cifrado(self, nombre: str) -> None:
        """RT04 (RN-29). Cambia el algoritmo con que se cifran los respaldos nuevos; los ya escritos se siguen
        descifrando con el algoritmo que anotaron. Un nombre desconocido es ``ValidacionError`` (campo ``nombre``)."""
        self._gestor.cambiar_algoritmo(nombre)

    def _repositorio_de(self, tipo_evento: str):
        """``"<Agregado>.<operación>"`` -> repositorio del agregado que lo respaldó."""
        repositorios = {
            "Usuario": self._usuarios,
            "Suscripcion": self._suscripciones,
            "Comision": self._comisiones,
            "SolicitudDominio": self._solicitudes,
        }
        repositorio = repositorios.get(tipo_evento.partition(".")[0])
        if repositorio is None:
            raise ReglaNegocioError(f"El evento {tipo_evento!r} no corresponde a ningún repositorio.")
        return repositorio

    def _revertir(self) -> None:
        try:
            self._unidad_trabajo.revertir()
        except Exception:  # la conexión puede estar rota: no debe tapar el error original
            _registro.exception("No se pudo revertir la sincronización")
