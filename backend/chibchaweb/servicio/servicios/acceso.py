"""Acceso (AUTH)."""

from __future__ import annotations

from chibchaweb.dominio.cuentas import Cliente
from chibchaweb.dominio.errores import (
    AutorizacionFallidaError,
    ErrorDominio,
    NoEncontradoError,
    UsuarioInactivoError,
    ValidacionError,
)
from chibchaweb.dominio.hospedaje import SitioWeb, Suscripcion
from chibchaweb.dominio.integraciones import (
    IdentidadExterna,
    ProveedorAutenticacion,
    ValidadorMedioPago,
)
from chibchaweb.dominio.repositorios import (
    RepositorioCatalogo,
    RepositorioSuscripcion,
    RepositorioUsuario,
)
from chibchaweb.servicio._tiempo import hoy
from chibchaweb.servicio.dto import (
    DatosClienteDTO,
    ResultadoAccesoDTO,
    ResumenDTO,
)
from chibchaweb.servicio.servicios._comun import (
    _buscar_paquete,
    _buscar_plan,
    _con_campo_dto,
    _direccion,
    _exigir_activo,
    _plataforma,
    _resultado_de,
    _subdominio,
    _tarjeta,
)


class ServicioAcceso:
    """Inicio de sesión con el proveedor externo y autoregistro de clientes (módulo AUTH)."""

    def __init__(
        self,
        proveedor: ProveedorAutenticacion,
        validador: ValidadorMedioPago,
        usuarios: RepositorioUsuario,
        catalogo: RepositorioCatalogo,
        suscripciones: RepositorioSuscripcion,
    ):
        self._proveedor = proveedor
        self._validador = validador
        self._usuarios = usuarios
        self._catalogo = catalogo
        self._suscripciones = suscripciones

    def iniciar_sesion(self, codigo_autorizacion: str) -> ResultadoAccesoDTO:
        """CU-AUTH-02. Busca por ``sub``; si no, por correo verificado (RN-07); si no, pide el registro."""
        try:
            identidad = self._proveedor.autorizar(codigo_autorizacion)
        except AutorizacionFallidaError:
            raise
        except ErrorDominio as exc:  # cualquier otra falla al verificar la identidad también es 401 (P-19)
            raise AutorizacionFallidaError("No se pudo verificar la identidad con el proveedor") from exc
        usuario = self._usuarios.buscar_por_identificador_externo(identidad.identificador_externo)
        if usuario is None and identidad.correo_verificado:
            candidato = self._usuarios.buscar_por_correo(identidad.correo)
            if candidato is not None and candidato.es_autenticable():
                _exigir_activo(candidato)
                candidato.vincular_cuenta(identidad)  # RN-06, RN-07
                usuario = candidato
        if usuario is None:
            return ResultadoAccesoDTO(
                registrado=False,
                nombre=identidad.nombre,
                correo=identidad.correo,
                tipo_usuario="",
                identificador_externo=identidad.identificador_externo,
            )
        _exigir_activo(usuario)
        usuario.cuenta.registrar_acceso()  # type: ignore[union-attr]
        self._usuarios.actualizar(usuario)
        return _resultado_de(usuario)

    def verificar_usuario_activo(self, id_usuario: int) -> ResultadoAccesoDTO:
        """Comprueba que el usuario de una sesión abierta sigue activo (RN-09) y devuelve su acceso actual (rol y
        operaciones vigentes). No es un CU: la autenticación de sesión lo llama en cada petición para que la baja
        o el cambio de cargo de un empleado se apliquen a sus sesiones abiertas (P-25)."""
        try:
            usuario = self._usuarios.buscar_por_id(id_usuario)
        except NoEncontradoError:
            raise UsuarioInactivoError("El usuario ya no existe") from None
        _exigir_activo(usuario)
        return _resultado_de(usuario)

    def registrarse(self, datos: DatosClienteDTO) -> int:
        """CU-AUTH-03. Crea cliente, direcciones, tarjeta, sitio y suscripción; devuelve el id del cliente."""
        if not datos.identificador_externo or not datos.correo:
            raise ValidacionError("correo", "No hay una identidad verificada para registrar")
        identidad = IdentidadExterna(datos.identificador_externo, datos.nombre or "", datos.correo, True)
        paquete = _buscar_paquete(self._catalogo, datos.id_paquete)
        plan = _buscar_plan(self._catalogo, datos.id_plan)
        plataforma = _plataforma(datos.plataforma)
        sitio = SitioWeb(_subdominio(datos.sitio), plataforma)
        cliente = Cliente(
            nombre=datos.nombre or "",
            correo=identidad.correo,
            telefono=datos.telefono or "",
            residencia=_direccion(datos.linea_residencia, datos.ciudad_residencia, datos.codigo_postal_residencia),
            facturacion=_direccion(datos.linea_facturacion, datos.ciudad_facturacion, datos.codigo_postal_facturacion),
            medio_pago=_tarjeta(datos, self._catalogo),
        )
        try:
            cliente.validar_datos_facturacion(self._validador)  # RN-10, RN-11
        except ValidacionError as error:
            raise _con_campo_dto(error) from None
        if datos.codigo_distribuidor:  # RN-13
            distribuidor = self._usuarios.buscar_distribuidor_por_codigo(datos.codigo_distribuidor)
            if distribuidor is None:
                raise ValidacionError("codigoDistribuidor", "El código de distribuidor no existe o está inactivo")
            cliente.asociar_distribuidor(distribuidor)
            distribuidor.agregar_referido(cliente)
        suscripcion = Suscripcion(cliente, sitio, paquete, plan, hoy())  # RN-04
        cliente.agregar_suscripcion(suscripcion)
        cliente.vincular_cuenta(identidad)
        id_cliente = self._usuarios.insertar(cliente)
        self._suscripciones.insertar(suscripcion)
        return id_cliente

    def consultar_paquetes(self) -> list[ResumenDTO]:
        return [
            ResumenDTO(p.id, p.nombre, f"{p.tarifa_mensual:.2f}", "ACTIVO")  # type: ignore[arg-type]
            for p in self._catalogo.listar_paquetes()
        ]

    def consultar_planes(self) -> list[ResumenDTO]:
        return [
            ResumenDTO(p.id, p.nombre, f"{p.meses}|{p.descuento:.2f}", "ACTIVO")  # type: ignore[arg-type]
            for p in self._catalogo.listar_planes()
        ]
