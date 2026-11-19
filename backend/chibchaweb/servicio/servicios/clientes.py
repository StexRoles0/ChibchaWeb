"""Clientes (CLI)."""

from __future__ import annotations

from chibchaweb.dominio.cuentas import Cliente
from chibchaweb.dominio.errores import (
    NoEncontradoError,
    ValidacionError,
)
from chibchaweb.dominio.hospedaje import Suscripcion
from chibchaweb.dominio.integraciones import (
    ValidadorMedioPago,
)
from chibchaweb.dominio.repositorios import (
    RepositorioCatalogo,
    RepositorioSuscripcion,
    RepositorioUsuario,
)
from chibchaweb.servicio.dto import (
    CategoriaPerfil,
    DatosClienteDTO,
    ResumenDTO,
)
from chibchaweb.servicio.servicios._comun import (
    _buscar_paquete,
    _buscar_plan,
    _como_cliente,
    _con_campo_dto,
    _direccion,
    _exigir_activo,
    _plataforma,
    _subdominio,
    _suscripcion_principal,
    _tarjeta,
)


class ServicioClientes:
    """Autogestión del perfil del cliente (módulo CLI)."""

    def __init__(
        self,
        validador: ValidadorMedioPago,
        usuarios: RepositorioUsuario,
        catalogo: RepositorioCatalogo,
        suscripciones: RepositorioSuscripcion,
    ):
        self._validador = validador
        self._usuarios = usuarios
        self._catalogo = catalogo
        self._suscripciones = suscripciones

    def modificar_perfil(self, id_cliente: int, categoria: CategoriaPerfil, datos: DatosClienteDTO) -> None:
        """CU-CLI-03. Aplica el bloque de ``categoria``; revalida dirección y tarjeta si cambian."""
        cliente = _como_cliente(self._usuarios.buscar_por_id(id_cliente))
        _exigir_activo(cliente)
        if categoria is CategoriaPerfil.PERSONAL:
            self._modificar_personal(cliente, datos)
        elif categoria is CategoriaPerfil.PAQUETE_PLAN:
            self._modificar_paquete_plan(cliente, datos)
        else:
            self._modificar_pago(cliente, datos)

    def _modificar_personal(self, cliente: Cliente, datos: DatosClienteDTO) -> None:
        if datos.nombre is not None:
            cliente.nombre = datos.nombre
        if datos.telefono is not None:
            cliente.telefono = datos.telefono
        if any((datos.linea_residencia, datos.ciudad_residencia, datos.codigo_postal_residencia)):
            actual = cliente.residencia
            nueva = _direccion(
                datos.linea_residencia if datos.linea_residencia is not None else actual.linea,
                datos.ciudad_residencia if datos.ciudad_residencia is not None else actual.ciudad,
                datos.codigo_postal_residencia if datos.codigo_postal_residencia is not None else actual.codigo_postal,
            )
            if not nueva.validar():  # RN-10
                raise ValidacionError("lineaResidencia", "La dirección de residencia no es válida")
            cliente.residencia = nueva
        suscripcion = self._suscripcion_de(cliente, datos.id_suscripcion) if datos.sitio or datos.plataforma else None
        if suscripcion is not None:
            if datos.sitio:
                suscripcion.sitio.subdominio = _subdominio(datos.sitio)
            if datos.plataforma:
                suscripcion.sitio.plataforma = _plataforma(datos.plataforma)
        self._usuarios.actualizar(cliente)
        if suscripcion is not None:
            self._suscripciones.actualizar(suscripcion)

    def _modificar_paquete_plan(self, cliente: Cliente, datos: DatosClienteDTO) -> None:
        if datos.id_suscripcion is None:
            raise ValidacionError("idSuscripcion", "Indique la suscripción que desea modificar")
        if datos.id_paquete is None and datos.id_plan is None:
            raise ValidacionError("idPaquete", "Indique el paquete o el plan nuevo")
        suscripcion = self._suscripcion_de(cliente, datos.id_suscripcion)
        if suscripcion is None:
            raise NoEncontradoError("El cliente no tiene suscripciones")
        if datos.id_paquete is not None:
            suscripcion.cambiar_paquete(_buscar_paquete(self._catalogo, datos.id_paquete))
        if datos.id_plan is not None:
            suscripcion.cambiar_plan(_buscar_plan(self._catalogo, datos.id_plan))
        self._suscripciones.actualizar(suscripcion)  # aplica desde el próximo corte: la fecha no se mueve

    def _modificar_pago(self, cliente: Cliente, datos: DatosClienteDTO) -> None:
        """D-22: la tarjeta se reingresa completa porque el código de seguridad no se guarda (RN-12)."""
        cliente.facturacion = _direccion(
            datos.linea_facturacion, datos.ciudad_facturacion, datos.codigo_postal_facturacion
        )
        cliente.medio_pago = _tarjeta(datos, self._catalogo)
        try:
            cliente.validar_datos_facturacion(self._validador)  # RN-10
        except ValidacionError as error:
            raise _con_campo_dto(error) from None
        self._usuarios.actualizar(cliente)

    @staticmethod
    def _suscripcion_de(cliente: Cliente, id_suscripcion: int | None) -> Suscripcion | None:
        if id_suscripcion is None:
            return _suscripcion_principal(cliente)
        for suscripcion in cliente.suscripciones:
            if suscripcion.id == id_suscripcion:
                return suscripcion
        raise NoEncontradoError("La suscripción no pertenece al cliente")

    def eliminar_perfil(self, id_cliente: int) -> None:
        """CU-CLI-02. Inactiva al cliente y suspende sus suscripciones (RN-09). Es idempotente."""
        cliente = _como_cliente(self._usuarios.buscar_por_id(id_cliente))
        if not cliente.activo:
            return
        for suscripcion in list(cliente.suscripciones):
            cliente.cancelar_suscripcion(suscripcion)
            self._suscripciones.actualizar(suscripcion)
        cliente.inactivar()
        self._usuarios.actualizar(cliente)

    def consultar_sitios(self, id_cliente: int) -> list[ResumenDTO]:
        """Sitios del cliente para el selector de M-10 (P-06). El id es el del sitio."""
        cliente = _como_cliente(self._usuarios.buscar_por_id(id_cliente))
        return [
            ResumenDTO(
                s.sitio.id,  # type: ignore[arg-type]
                s.sitio.subdominio,
                f"{s.sitio.plataforma.value} · {s.paquete.nombre}",
                "ACTIVA" if s.activa else "SUSPENDIDA",
            )
            for s in cliente.suscripciones
        ]
