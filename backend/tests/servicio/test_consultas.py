"""CU-CON-01 y CU-CON-02, y CU-CLI-01 (detalle del cliente): ServicioConsultas con repositorios en memoria."""

import pytest

from chibchaweb.dominio.errores import NoEncontradoError
from chibchaweb.dominio.soporte import CategoriaTicket, Ticket
from chibchaweb.servicio.dto import DetalleDTO, ResumenDTO, TipoEntidad


def como_dict(detalle: DetalleDTO) -> dict[str, list[str]]:
    salida: dict[str, list[str]] = {}
    for campo in detalle.campos:
        clave, _, valor = campo.partition(": ")
        salida.setdefault(clave, []).append(valor)
    return salida


@pytest.fixture
def ticket(tickets, catalogo, cliente_registrado, empleado_soporte):
    t = Ticket(
        "El sitio no carga",
        CategoriaTicket.RENDIMIENTO,
        cliente_registrado,
        catalogo.buscar_nivel_inicial(),
        sitio_afectado=cliente_registrado.suscripciones[0].sitio,
    )
    tickets.insertar(t)
    return t


# --- CON-01 --------------------------------------------------------------------------------------
def test_basico_de_clientes(consultas, cliente_registrado):
    (fila,) = consultas.consultar_basico(TipoEntidad.CLIENTE, "")
    assert fila == ResumenDTO(
        cliente_registrado.id, "Laura Gómez", "laura@correo.co · tiendalaura.chibchaweb.com · Chibcha-Oro", "ACTIVO"
    )


def test_basico_de_clientes_inactivo_y_sin_suscripcion(consultas, cliente_registrado):
    cliente_registrado.inactivar()
    cliente_registrado._suscripciones.clear()
    (fila,) = consultas.consultar_basico(TipoEntidad.CLIENTE, "laura")
    assert fila.estado == "INACTIVO" and fila.subtitulo == "laura@correo.co · sin sitio · sin paquete"


def test_basico_de_empleados_distribuidores_y_filtro(consultas, empleado_soporte, empleado_gestion, distribuidor):
    assert [(f.titulo, f.subtitulo) for f in consultas.consultar_basico(TipoEntidad.EMPLEADO, "")] == [
        ("Sergio Soporte", "E-1002 · Soporte"),
        ("Gabriela Gestión", "E-1001 · Gestión"),
    ]
    assert [f.titulo for f in consultas.consultar_basico(TipoEntidad.EMPLEADO, "  GABRIELA ")] == ["Gabriela Gestión"]
    (d,) = consultas.consultar_basico(TipoEntidad.DISTRIBUIDOR, "")
    assert d.subtitulo == "900123456 · DIS-ANDES1 · 0 referidos" and d.estado == "ACTIVO"
    assert consultas.consultar_basico(TipoEntidad.DISTRIBUIDOR, "zzz") == []


def test_basico_de_tickets(consultas, ticket):
    (fila,) = consultas.consultar_basico(TipoEntidad.TICKET, "")
    assert fila == ResumenDTO(ticket.id, "RENDIMIENTO", "Soporte", "ABIERTO")
    assert consultas.consultar_basico(TipoEntidad.TICKET, "no carga")[0].id == ticket.id
    assert consultas.consultar_basico(TipoEntidad.TICKET, "otra cosa") == []


# --- CON-02 / CLI-01 -----------------------------------------------------------------------------
def test_detalle_de_cliente_con_las_claves_fijas_de_api(consultas, cliente_registrado):
    d = consultas.consultar_detalle(TipoEntidad.CLIENTE, cliente_registrado.id)
    assert d.id == cliente_registrado.id and d.titulo == "Laura Gómez"
    assert [c.partition(":")[0] for c in d.campos] == [
        "nombre", "correo", "telefono", "lineaResidencia", "ciudadResidencia", "codigoPostalResidencia",
        "lineaFacturacion", "ciudadFacturacion", "codigoPostalFacturacion", "tarjeta", "franquicia", "vencimiento",
        "idSuscripcion", "sitio", "plataforma", "idPaquete", "paquete", "idPlan", "plan", "montoPeriodo",
        "fechaCorte", "distribuidor", "activo",
    ]  # fmt: skip
    v = {k: x[0] for k, x in como_dict(d).items()}
    assert v["tarjeta"] == "VISA •••• 4242" and "4242424242424242" not in " ".join(d.campos)  # RN-12
    assert v["sitio"] == "tiendalaura.chibchaweb.com" and v["plataforma"] == "UNIX"
    assert (v["paquete"], v["plan"], v["montoPeriodo"]) == ("Chibcha-Oro", "Semestral", "54.00")  # RN-01
    assert (v["idPaquete"], v["idPlan"], v["activo"], v["distribuidor"]) == ("2", "3", "true", "")
    assert v["vencimiento"] == "2099-12-01" and v["franquicia"] == "VISA"


def test_detalle_de_cliente_con_distribuidor(consultas, acceso, usuarios, distribuidor, datos_registro):
    id = acceso.registrarse(datos_registro(codigo_distribuidor="DIS-ANDES1"))
    assert como_dict(consultas.consultar_detalle(TipoEntidad.CLIENTE, id))["distribuidor"] == ["DIS-ANDES1"]


def test_detalle_de_empleado(consultas, empleado_gestion):
    v = como_dict(consultas.consultar_detalle(TipoEntidad.EMPLEADO, empleado_gestion.id))
    assert (v["documento"], v["idRol"], v["rol"], v["activo"]) == (["E-1001"], ["1"], ["Gestión"], ["true"])
    assert v["fechaRegistro"][0].startswith("20")


def test_detalle_de_distribuidor_con_categoria(consultas, distribuidor):
    v = como_dict(consultas.consultar_detalle(TipoEntidad.DISTRIBUIDOR, distribuidor.id))
    assert (v["codigo"], v["categoria"], v["referidos"]) == (["DIS-ANDES1"], ["Básico"], ["0"])  # RN-19


def test_detalle_de_ticket_con_movimientos(consultas, ticket, tickets, catalogo, empleado_soporte):
    ticket.escalar(catalogo.buscar_nivel_siguiente(ticket.nivel_actual), empleado_soporte, "Lo reviso mañana")
    d = consultas.consultar_detalle(TipoEntidad.TICKET, ticket.id)
    v = como_dict(d)
    assert d.titulo == f"Ticket #{ticket.id}"
    assert (v["categoria"], v["estado"], v["nivel"], v["reportante"]) == (
        ["RENDIMIENTO"], ["ESCALADO"], ["Gestión"], ["Laura Gómez (cliente)"],
    )  # fmt: skip
    assert v["sitio"] == ["tiendalaura.chibchaweb.com"] and v["descripcion"] == ["El sitio no carga"]
    (movimiento,) = v["movimiento"]
    fecha, responsable, estado, nivel, observacion = movimiento.split("|")
    assert (responsable, estado, nivel, observacion) == ("Sergio Soporte", "ESCALADO", "Gestión", "Lo reviso mañana")
    assert len(fecha) == 16 and fecha[10] == " "


def test_detalle_de_ticket_sin_sitio_ni_movimientos(consultas, tickets, catalogo, cliente_registrado):
    t = Ticket("Otra novedad", CategoriaTicket.OTRA, cliente_registrado, catalogo.buscar_nivel_inicial())
    tickets.insertar(t)
    v = como_dict(consultas.consultar_detalle(TipoEntidad.TICKET, t.id))
    assert v["sitio"] == [""] and "movimiento" not in v


@pytest.mark.parametrize("tipo", [TipoEntidad.EMPLEADO, TipoEntidad.DISTRIBUIDOR])
def test_detalle_de_otro_tipo_de_usuario_es_404(consultas, cliente_registrado, tipo):
    with pytest.raises(NoEncontradoError):
        consultas.consultar_detalle(tipo, cliente_registrado.id)


@pytest.mark.parametrize("tipo", list(TipoEntidad))
def test_detalle_inexistente_es_404(consultas, tipo):
    with pytest.raises(NoEncontradoError):
        consultas.consultar_detalle(tipo, 9999)
