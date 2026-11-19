"""Dominios (DOM): registro y envío de la solicitud de dominio (CU-DOM-01, CU-DOM-02)."""

from __future__ import annotations

import threading

from chibchaweb.dominio.dominios_web import ConstructorSolicitud, EstadoSolicitud, SolicitudDominio
from chibchaweb.dominio.errores import EstadoInvalidoError
from chibchaweb.dominio.integraciones import RegistradorDominio
from chibchaweb.dominio.repositorios import RepositorioSolicitudDominio, RepositorioUsuario
from chibchaweb.servicio._tiempo import ZONA
from chibchaweb.servicio.dto import ResumenDTO
from chibchaweb.servicio.servicios._comun import _como_cliente, _exigir_activo


class ServicioDominios:
    """Registro y envío de solicitudes de dominio (módulo DOM)."""

    def __init__(
        self,
        constructor: ConstructorSolicitud,
        registrador: RegistradorDominio,
        solicitudes: RepositorioSolicitudDominio,
        usuarios: RepositorioUsuario,
    ):
        self._constructor = constructor
        self._registrador = registrador
        self._solicitudes = solicitudes
        self._usuarios = usuarios
        self._candado = threading.Lock()  # el constructor inyectado guarda estado: un documento a la vez

    def registrar_solicitud_dominio(self, id_cliente: int, nombre: str, extension: str) -> int:
        """CU-DOM-01 (RN-16). Crea la solicitud REGISTRADA; si el formato es inválido no se guarda (422)."""
        cliente = _como_cliente(self._usuarios.buscar_por_id(id_cliente))
        _exigir_activo(cliente)
        solicitud = SolicitudDominio(nombre, extension, cliente)
        solicitud.validar_formato()  # lanza ValidacionError con el campo que falló (nombre o extension)
        return self._solicitudes.insertar(solicitud)

    def generar_y_enviar_solicitud_xml(self, id_solicitud: int) -> EstadoSolicitud:
        """CU-DOM-02 (RN-17, RN-18). Arma el XML con el Builder, lo envía y guarda ENVIADA o FALLIDA."""
        solicitud = self._solicitudes.buscar_por_id(id_solicitud)
        if not solicitud.esta_pendiente():
            raise EstadoInvalidoError("Solo se puede enviar una solicitud pendiente")
        with self._candado:
            documento = solicitud.construir_documento(self._constructor)
        solicitud.enviar_a(self._registrador, documento)  # el registrador caído deja la solicitud FALLIDA
        self._solicitudes.actualizar(solicitud)
        return solicitud.estado

    def consultar_solicitudes(self, id_cliente: int) -> list[ResumenDTO]:
        """Solicitudes del cliente, de la más reciente a la más antigua; subtitulo = fecha ``AAAA-MM-DD``."""
        solicitudes = sorted(
            self._solicitudes.buscar_por_solicitante(id_cliente),
            key=lambda s: (s.fecha_solicitud, s.id or 0),
            reverse=True,
        )
        return [
            ResumenDTO(
                s.id,  # type: ignore[arg-type]
                s.nombre_completo(),
                s.fecha_solicitud.astimezone(ZONA).date().isoformat(),
                s.estado.value,
            )
            for s in solicitudes
        ]
