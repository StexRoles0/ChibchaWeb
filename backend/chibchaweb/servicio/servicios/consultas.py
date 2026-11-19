"""Consultas (CON)."""

from __future__ import annotations

from chibchaweb.dominio.cuentas import Cliente, Distribuidor, Empleado, TarjetaCredito
from chibchaweb.dominio.errores import (
    NoEncontradoError,
)
from chibchaweb.dominio.facturacion import CategoriaBasica, CategoriaPremium
from chibchaweb.dominio.repositorios import (
    RepositorioTicket,
    RepositorioUsuario,
)
from chibchaweb.dominio.soporte import MovimientoTicket
from chibchaweb.servicio._tiempo import ZONA
from chibchaweb.servicio.dto import (
    DetalleDTO,
    ResumenDTO,
    TipoEntidad,
)
from chibchaweb.servicio.servicios._comun import (
    _campos,
    _estado,
    _resumen_ticket,
    _suscripcion_principal,
)

_CATEGORIAS = (CategoriaBasica(), CategoriaPremium())  # estrategias RN-19, para mostrar la categoría


class ServicioConsultas:
    """Consultas básica y detallada parametrizadas por tipo de entidad (módulo CON)."""

    def __init__(self, usuarios: RepositorioUsuario, tickets: RepositorioTicket):
        self._usuarios = usuarios
        self._tickets = tickets

    def consultar_basico(self, tipo_entidad: TipoEntidad, filtro: str) -> list[ResumenDTO]:
        """CU-CON-01. Listado resumido; el filtro lo resuelve el repositorio (sin distinguir mayúsculas)."""
        filtro = (filtro or "").strip()
        if tipo_entidad is TipoEntidad.CLIENTE:
            return [self._resumen_cliente(c) for c in self._usuarios.buscar_clientes(filtro)]
        if tipo_entidad is TipoEntidad.EMPLEADO:
            return [
                ResumenDTO(e.id, e.nombre, f"{e.documento} · {e.rol.nombre}", _estado(e))  # type: ignore[arg-type]
                for e in self._usuarios.buscar_empleados(filtro)
            ]
        if tipo_entidad is TipoEntidad.DISTRIBUIDOR:
            return [
                ResumenDTO(  # type: ignore[arg-type]
                    d.id, d.nombre, f"{d.documento} · {d.codigo} · {d.cantidad_referidos()} referidos", _estado(d)
                )
                for d in self._usuarios.buscar_distribuidores(filtro)
            ]
        return [_resumen_ticket(t) for t in self._tickets.buscar_por_filtro(filtro)]

    def consultar_detalle(self, tipo_entidad: TipoEntidad, id: int) -> DetalleDTO:
        """CU-CON-02. Vista ampliada con las claves fijas de api.md."""
        if tipo_entidad is TipoEntidad.TICKET:
            return self._detalle_ticket(id)
        usuario = self._usuarios.buscar_por_id(id)
        tipos = {
            TipoEntidad.CLIENTE: (Cliente, self._detalle_cliente),
            TipoEntidad.EMPLEADO: (Empleado, self._detalle_empleado),
            TipoEntidad.DISTRIBUIDOR: (Distribuidor, self._detalle_distribuidor),
        }
        clase, armar = tipos[tipo_entidad]
        if not isinstance(usuario, clase):
            raise NoEncontradoError(f"No existe {tipo_entidad.value.lower()} con id {id}")
        return armar(usuario)  # type: ignore[operator]

    # --- resúmenes ----------------------------------------------------------------------------
    @staticmethod
    def _resumen_cliente(c: Cliente) -> ResumenDTO:
        s = _suscripcion_principal(c)
        sitio = s.sitio.subdominio if s else "sin sitio"
        paquete = s.paquete.nombre if s else "sin paquete"
        return ResumenDTO(c.id, c.nombre, f"{c.correo} · {sitio} · {paquete}", _estado(c))  # type: ignore[arg-type]

    # --- detalles -----------------------------------------------------------------------------
    @staticmethod
    def _detalle_cliente(c: Cliente) -> DetalleDTO:
        s = _suscripcion_principal(c)
        tarjeta = c.medio_pago
        pares: list[tuple[str, object]] = [
            ("nombre", c.nombre),
            ("correo", c.correo),
            ("telefono", c.telefono),
            ("lineaResidencia", c.residencia.linea),
            ("ciudadResidencia", c.residencia.ciudad),
            ("codigoPostalResidencia", c.residencia.codigo_postal),
            ("lineaFacturacion", c.facturacion.linea),
            ("ciudadFacturacion", c.facturacion.ciudad),
            ("codigoPostalFacturacion", c.facturacion.codigo_postal),
            ("tarjeta", tarjeta.descripcion()),  # RN-12: enmascarada
            ("franquicia", tarjeta.franquicia.nombre if isinstance(tarjeta, TarjetaCredito) else ""),
            ("vencimiento", tarjeta.vencimiento.isoformat() if isinstance(tarjeta, TarjetaCredito) else ""),
            ("idSuscripcion", s.id if s else None),
            ("sitio", s.sitio.subdominio if s else None),
            ("plataforma", s.sitio.plataforma.value if s else None),
            ("idPaquete", s.paquete.id if s else None),
            ("paquete", s.paquete.nombre if s else None),
            ("idPlan", s.plan.id if s else None),
            ("plan", s.plan.nombre if s else None),
            ("montoPeriodo", f"{s.monto_del_periodo():.2f}" if s else None),
            ("fechaCorte", s.fecha_corte.isoformat() if s else None),
            ("distribuidor", c.distribuidor.codigo if c.distribuidor else None),
            ("activo", c.activo),
        ]
        return DetalleDTO(c.id, c.nombre, _campos(pares))  # type: ignore[arg-type]

    @staticmethod
    def _detalle_empleado(e: Empleado) -> DetalleDTO:
        pares: list[tuple[str, object]] = [
            ("nombre", e.nombre),
            ("documento", e.documento),
            ("correo", e.correo),
            ("telefono", e.telefono),
            ("idRol", e.rol.id),
            ("rol", e.rol.nombre),
            ("activo", e.activo),
            ("fechaRegistro", e.fecha_registro.astimezone(ZONA).isoformat()),
        ]
        return DetalleDTO(e.id, e.nombre, _campos(pares))  # type: ignore[arg-type]

    @staticmethod
    def _detalle_distribuidor(d: Distribuidor) -> DetalleDTO:
        pares: list[tuple[str, object]] = [
            ("nombre", d.nombre),
            ("documento", d.documento),
            ("correo", d.correo),
            ("telefono", d.telefono),
            ("codigo", d.codigo),
            ("categoria", d.determinar_categoria(list(_CATEGORIAS)).nombre()),
            ("referidos", d.cantidad_referidos()),
            ("activo", d.activo),
        ]
        return DetalleDTO(d.id, d.nombre, _campos(pares))  # type: ignore[arg-type]

    def _detalle_ticket(self, id: int) -> DetalleDTO:
        t = self._tickets.buscar_por_id(id)
        pares: list[tuple[str, object]] = [
            ("categoria", t.categoria.value),
            ("estado", t.estado.value),
            ("nivel", t.nivel_actual.nombre),
            (
                "reportante",
                f"{t.reportante.nombre} ({'empleado' if isinstance(t.reportante, Empleado) else 'cliente'})",
            ),
            ("sitio", t.sitio_afectado.subdominio if t.sitio_afectado else None),
            ("fechaCreacion", t.fecha_creacion.astimezone(ZONA).isoformat()),
            ("descripcion", t.descripcion),
        ]
        for m in sorted(t.movimientos, key=lambda x: x.fecha):
            pares.append(("movimiento", self._movimiento(m)))
        return DetalleDTO(t.id, f"Ticket #{t.id}", _campos(pares))  # type: ignore[arg-type]

    @staticmethod
    def _movimiento(m: MovimientoTicket) -> str:
        return (
            f"{m.fecha.astimezone(ZONA):%Y-%m-%d %H:%M}|{m.responsable.nombre}|{m.estado_resultante.value}|"
            f"{m.nivel_resultante.nombre}|{m.observacion}"
        )
