"""Auxiliares compartidos por los servicios (privados del paquete)."""

from __future__ import annotations

from chibchaweb.dominio.cuentas import Cliente, Direccion, Empleado, TarjetaCredito, Usuario
from chibchaweb.dominio.errores import (
    NoEncontradoError,
    UsuarioInactivoError,
    ValidacionError,
)
from chibchaweb.dominio.hospedaje import Plataforma, Suscripcion
from chibchaweb.dominio.repositorios import (
    RepositorioCatalogo,
)
from chibchaweb.dominio.soporte import Ticket
from chibchaweb.servicio.dto import (
    DatosClienteDTO,
    ResultadoAccesoDTO,
    ResumenDTO,
)

SUFIJO_SUBDOMINIO = ".chibchaweb.com"  # P-15
_PAIS = "Colombia"  # D-11
_CAMPO_DTO = {"residencia": "lineaResidencia", "facturacion": "lineaFacturacion"}


# --------------------------------------------------------------------------------------------------
# Auxiliares compartidos (privados del módulo)
# --------------------------------------------------------------------------------------------------


def _estado(usuario: Usuario) -> str:
    return "ACTIVO" if usuario.activo else "INACTIVO"


def _campos(pares: list[tuple[str, object]]) -> tuple[str, ...]:
    """``"clave: valor"``; los booleanos van en minúscula y ``None`` como cadena vacía."""
    salida = []
    for clave, valor in pares:
        if isinstance(valor, bool):
            valor = str(valor).lower()
        salida.append(f"{clave}: {'' if valor is None else valor}")
    return tuple(salida)


def _suscripcion_principal(cliente: Cliente) -> Suscripcion | None:
    """La primera suscripción activa del cliente o, si no hay, la primera que tenga."""
    activas = [s for s in cliente.suscripciones if s.activa]
    candidatas = activas or list(cliente.suscripciones)
    return candidatas[0] if candidatas else None


def _como_cliente(usuario: Usuario) -> Cliente:
    if not isinstance(usuario, Cliente):
        raise NoEncontradoError("No existe el cliente")
    return usuario


def _con_campo_dto(error: ValidacionError) -> ValidacionError:
    """Traduce el nombre de campo del dominio al del DTO para que la pantalla marque el campo correcto."""
    return ValidacionError(_CAMPO_DTO.get(error.campo, error.campo), error.mensaje)


def _subdominio(sitio: str | None) -> str:
    nombre = (sitio or "").strip().lower().removesuffix(SUFIJO_SUBDOMINIO)
    return f"{nombre}{SUFIJO_SUBDOMINIO}"


def _plataforma(valor: str | None) -> Plataforma:
    try:
        return Plataforma((valor or "").strip().upper())
    except ValueError:
        raise ValidacionError("plataforma", "La plataforma debe ser WINDOWS o UNIX") from None


def _direccion(linea: str | None, ciudad: str | None, codigo_postal: str | None) -> Direccion:
    return Direccion(linea or "", ciudad or "", codigo_postal or "", _PAIS)


def _tarjeta(datos: DatosClienteDTO, catalogo: RepositorioCatalogo) -> TarjetaCredito:
    try:
        franquicia = catalogo.buscar_franquicia(datos.franquicia or "")
    except NoEncontradoError:
        raise ValidacionError("franquicia", "La franquicia no es válida") from None
    return TarjetaCredito(datos.numero_tarjeta or "", datos.vencimiento, franquicia, datos.codigo_seguridad)  # type: ignore[arg-type]


def _buscar_paquete(catalogo: RepositorioCatalogo, id: int | None):
    try:
        return catalogo.buscar_paquete(id)  # type: ignore[arg-type]
    except NoEncontradoError:
        raise ValidacionError("idPaquete", "El paquete no existe") from None


def _buscar_plan(catalogo: RepositorioCatalogo, id: int | None):
    try:
        return catalogo.buscar_plan(id)  # type: ignore[arg-type]
    except NoEncontradoError:
        raise ValidacionError("idPlan", "El plan no existe") from None


def _resultado_de(usuario: Usuario) -> ResultadoAccesoDTO:
    empleado = usuario if isinstance(usuario, Empleado) else None
    return ResultadoAccesoDTO(
        registrado=True,
        id_usuario=usuario.id,
        nombre=usuario.nombre,
        correo=usuario.correo,
        tipo_usuario="EMPLEADO" if empleado else "CLIENTE",
        rol=empleado.rol.nombre if empleado else None,
        operaciones=tuple(empleado.rol.operaciones) if empleado else (),
    )


def _resumen_ticket(t: Ticket) -> ResumenDTO:
    """Fila de ticket: titulo = categoría, subtitulo = nombre del nivel (D-28)."""
    return ResumenDTO(t.id, t.categoria.value, t.nivel_actual.nombre, t.estado.value)  # type: ignore[arg-type]


def _exigir_activo(usuario: Usuario) -> None:
    if not usuario.activo:
        raise UsuarioInactivoError("El usuario está inactivo")  # RN-09
