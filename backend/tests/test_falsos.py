"""Los dobles de tests/falsos.py cumplen sus interfaces del dominio y el comportamiento de D-05/D-06."""

import inspect
from datetime import date, datetime
from decimal import Decimal

import pytest

from chibchaweb.dominio import integraciones, repositorios
from chibchaweb.dominio._comun import ZONA
from chibchaweb.dominio.cuentas import Cliente, Direccion, Distribuidor, Empleado, TarjetaCredito
from chibchaweb.dominio.dominios_web import SolicitudDominio
from chibchaweb.dominio.errores import ContingenciaActivaError, ErrorDominio, NoEncontradoError
from chibchaweb.dominio.facturacion import Comision, EstadoPago, Pago
from chibchaweb.dominio.hospedaje import Plataforma, SitioWeb, Suscripcion
from chibchaweb.dominio.migracion import CreadorPagoLegado, ProcesoMigracion
from chibchaweb.dominio.soporte import CategoriaTicket, Ticket
from tests import falsos

PARES = [
    (repositorios.RepositorioUsuario, falsos.RepositorioUsuarioEnMemoria),
    (repositorios.RepositorioSuscripcion, falsos.RepositorioSuscripcionEnMemoria),
    (repositorios.RepositorioComision, falsos.RepositorioComisionEnMemoria),
    (repositorios.RepositorioSolicitudDominio, falsos.RepositorioSolicitudDominioEnMemoria),
    (repositorios.RepositorioTicket, falsos.RepositorioTicketEnMemoria),
    (repositorios.RepositorioMigracion, falsos.RepositorioMigracionEnMemoria),
    (repositorios.RepositorioCatalogo, falsos.RepositorioCatalogoEnMemoria),
    (repositorios.UnidadDeTrabajo, falsos.UnidadDeTrabajoEnMemoria),
    (integraciones.ProveedorAutenticacion, falsos.ProveedorAutenticacionFalso),
    (integraciones.ValidadorMedioPago, falsos.ValidadorMedioPagoFalso),
    (integraciones.PasarelaPago, falsos.PasarelaPagoFalsa),
    (integraciones.RegistradorDominio, falsos.RegistradorDominioFalso),
    (integraciones.FuenteLegada, falsos.FuenteLegadaFalsa),
]


@pytest.mark.parametrize(("interfaz", "falso"), PARES)
def test_falso_implementa_toda_la_interfaz(interfaz, falso):
    assert issubclass(falso, interfaz)
    assert not inspect.isabstract(falso)
    assert interfaz.__abstractmethods__  # la interfaz sí es abstracta
    for nombre in interfaz.__abstractmethods__:
        firma_interfaz = inspect.signature(getattr(interfaz, nombre))
        firma_falso = inspect.signature(getattr(falso, nombre))
        assert list(firma_falso.parameters) == list(firma_interfaz.parameters), nombre
    falso()


def test_hay_un_repositorio_en_memoria_por_interfaz():
    interfaces = {n for n, c in vars(repositorios).items() if inspect.isclass(c) and n.startswith("Repositorio")}
    assert interfaces == {i.__name__ for i, _ in PARES if i.__name__.startswith("Repositorio")}
    assert len(interfaces) == 7


def _cliente(correo="laura@correo.co", visa=None, numero="4242424242424242"):
    visa = visa or falsos.franquicias_estandar()[0]
    return Cliente(
        "Laura",
        correo,
        "1",
        Direccion("Calle 1", "Bogotá", "110111"),
        Direccion("Calle 2", "Bogotá", "110111"),
        TarjetaCredito(numero, date(2030, 1, 1), visa),
    )


def test_repositorio_usuario_en_memoria():
    repo = falsos.RepositorioUsuarioEnMemoria()
    catalogo = falsos.RepositorioCatalogoEnMemoria()
    cliente = _cliente()
    empleado = Empleado("Sergio", "soporte@chibchaweb.co", "1", "E-1", catalogo.buscar_rol(2))
    dist = Distribuidor("Andes", "a@andes.co", "1", "9", "DIS-ANDES1")
    ids = [repo.insertar(u) for u in (cliente, empleado, dist)]
    assert ids == [1, 2, 3] and cliente.id == 1
    assert repo.buscar_por_id(2) is empleado
    with pytest.raises(NoEncontradoError):
        repo.buscar_por_id(99)
    assert repo.buscar_por_correo("SOPORTE@chibchaweb.co") is empleado
    assert repo.buscar_por_correo("nadie@x.co") is None
    assert repo.buscar_clientes("") == [cliente] and repo.buscar_empleados("serg") == [empleado]
    assert repo.buscar_distribuidores("andes") == [dist] and len(repo.buscar_por_filtro("")) == 3
    assert repo.buscar_distribuidor_por_codigo("DIS-ANDES1") is dist
    cliente.vincular_cuenta(integraciones.IdentidadExterna("sub-1", "L", "laura@correo.co", True))
    repo.actualizar(cliente)
    assert repo.buscar_por_identificador_externo("sub-1") is cliente
    assert repo.buscar_por_identificador_externo("otro") is None
    repo.inactivar(3)
    assert repo.buscar_distribuidor_por_codigo("DIS-ANDES1") is None
    with pytest.raises(NoEncontradoError):
        repo.actualizar(_cliente(correo="nuevo@x.co"))
    repo.fallar_con = ContingenciaActivaError("BD caída")
    with pytest.raises(ContingenciaActivaError):
        repo.insertar(_cliente(correo="otro@x.co"))
    repo.fallar_restaurar_en = 1
    repo.restaurar("a")
    with pytest.raises(ErrorDominio):
        repo.restaurar("b")
    assert repo.restaurados == ["a"]


def test_repositorio_suscripcion_y_pagos_para_comision():
    repo = falsos.RepositorioSuscripcionEnMemoria()
    catalogo = falsos.RepositorioCatalogoEnMemoria()
    dist = Distribuidor("Andes", "a@andes.co", "1", "9", "DIS-ANDES1", id=1)
    cliente = _cliente()
    cliente.id = 5
    cliente.asociar_distribuidor(dist)
    s = Suscripcion(
        cliente,
        SitioWeb("laura.chibchaweb.co", Plataforma.UNIX),
        catalogo.buscar_paquete(2),
        catalogo.buscar_plan(3),
        date(2026, 11, 1),
    )
    assert repo.insertar(s) == 1 and s.sitio.id == 1
    pago = Pago(
        Decimal("54"), EstadoPago.EXITOSO, s, fecha=datetime(2026, 11, 2, tzinfo=ZONA), referencia_franquicia="R"
    )
    s.agregar_pago(pago)
    repo.registrar_pago(pago)
    assert pago.id == 1 and repo.pagos[1] is pago
    assert repo.buscar_vencidas(date(2026, 11, 1)) == [s] and repo.buscar_vencidas(date(2026, 10, 1)) == []
    assert repo.buscar_pagos_para_comision(dist, date(2026, 11, 1), date(2026, 11, 30)) == [pago]
    assert repo.buscar_pagos_para_comision(dist, date(2026, 12, 1), date(2026, 12, 31)) == []
    otro = Distribuidor("B", "b@x.co", "1", "9", "DIS-BBBBB1", id=2)
    assert repo.buscar_pagos_para_comision(otro, date(2026, 11, 1), date(2026, 11, 30)) == []
    assert repo.buscar_sitio(1) is s.sitio and repo.buscar_por_filtro("laura") == [s]
    with pytest.raises(NoEncontradoError):
        repo.buscar_sitio(9)
    repo.actualizar(s)
    assert repo.buscar_por_id(1) is s
    repo.restaurar("x")


def test_repositorios_comision_solicitud_ticket_migracion():
    catalogo = falsos.RepositorioCatalogoEnMemoria()
    dist = Distribuidor("Andes", "a@andes.co", "1", "9", "DIS-ANDES1", id=1)
    comisiones = falsos.RepositorioComisionEnMemoria()
    comision = Comision(date(2026, 11, 1), date(2026, 11, 30), 1, "Básico", Decimal("0.10"), dist)
    comisiones.insertar(comision)
    comisiones.registrar_cheque(comision)
    comisiones.actualizar(comision)
    assert comisiones.buscar_por_id(1) is comision and comisiones.buscar_por_filtro("andes") == [comision]
    assert comisiones.cheques_registrados == [1]
    comisiones.restaurar("x")

    cliente = _cliente()
    cliente.id = 7
    solicitudes = falsos.RepositorioSolicitudDominioEnMemoria()
    solicitud = SolicitudDominio("tienda", ".co", cliente)
    solicitudes.insertar(solicitud)
    solicitudes.actualizar(solicitud)
    assert solicitudes.buscar_por_id(1) is solicitud and solicitudes.buscar_por_solicitante(7) == [solicitud]
    assert solicitudes.buscar_por_filtro("tienda.co") == [solicitud]
    solicitudes.restaurar("x")

    tickets = falsos.RepositorioTicketEnMemoria()
    ticket = Ticket("caído", CategoriaTicket.RENDIMIENTO, cliente, catalogo.buscar_nivel_inicial())
    tickets.insertar(ticket)
    tickets.actualizar(ticket)
    assert tickets.buscar_por_id(1) is ticket and tickets.buscar_abiertos() == [ticket]
    assert tickets.buscar_creados_el(ticket.fecha_creacion.date()) == [ticket]
    assert tickets.buscar_por_reportante(7) == [ticket] and tickets.buscar_por_filtro("caído") == [ticket]

    migraciones = falsos.RepositorioMigracionEnMemoria()
    empleado = Empleado("Ana", "admin@chibchaweb.co", "1", "E-3", catalogo.buscar_rol(3))
    proceso = ProcesoMigracion(empleado, [CreadorPagoLegado()])
    migraciones.insertar(proceso)
    migraciones.actualizar(proceso)
    assert migraciones.buscar_por_id(1) is proceso and migraciones.buscar_por_filtro("CREADA") == [proceso]


def test_repositorio_catalogo_en_memoria():
    catalogo = falsos.RepositorioCatalogoEnMemoria()
    assert len(catalogo.listar_paquetes()) == 3 and len(catalogo.listar_planes()) == 4
    assert len(catalogo.listar_roles()) == 3 and catalogo.buscar_rol(2).nombre == "Soporte"
    assert catalogo.buscar_plan(3).nombre == "Semestral" and catalogo.buscar_franquicia("visa").nombre == "VISA"
    inicial = catalogo.buscar_nivel_inicial()
    gestion = catalogo.buscar_nivel_siguiente(inicial)
    desarrollo = catalogo.buscar_nivel_siguiente(gestion)
    assert (inicial.orden, gestion.orden, desarrollo.orden) == (1, 2, 3)
    assert catalogo.buscar_nivel_siguiente(desarrollo) is None
    with pytest.raises(NoEncontradoError):
        catalogo.buscar_paquete(99)
    with pytest.raises(NoEncontradoError):
        catalogo.buscar_franquicia("AMEX")


def test_unidad_de_trabajo_en_memoria():
    uow = falsos.UnidadDeTrabajoEnMemoria()
    uow.iniciar()
    assert uow.activa
    uow.revertir()
    uow.iniciar()
    uow.confirmar()
    assert uow.llamadas == ["iniciar", "revertir", "iniciar", "confirmar"] and not uow.activa


def test_adaptadores_falsos_d05_d06():
    identidad = falsos.ProveedorAutenticacionFalso().autorizar("dev:laura.gomez@correo.co")
    assert identidad.identificador_externo == "dev|laura.gomez@correo.co" and identidad.correo_verificado
    assert identidad.nombre == "Laura Gomez"
    assert not falsos.ProveedorAutenticacionFalso().autorizar("dev-noverificado:a@b.co").correo_verificado
    with pytest.raises(ErrorDominio):
        falsos.ProveedorAutenticacionFalso().autorizar("codigo-real")

    validador = falsos.ValidadorMedioPagoFalso()
    assert validador.verificar(_cliente().medio_pago) is True
    assert validador.verificar(_cliente(numero="4000000000000002").medio_pago) is False

    pasarela = falsos.PasarelaPagoFalsa()
    referencia = pasarela.cobrar(_cliente().medio_pago, Decimal("54.00"))
    assert referencia.startswith("REF-") and len(referencia) == 12
    assert pasarela.cobrar(_cliente(numero="4000000000000341").medio_pago, Decimal("1")) == ""

    registrador = falsos.RegistradorDominioFalso()
    registrador.enviar("<dominio>tienda</dominio>")
    with pytest.raises(ConnectionError):
        registrador.enviar("<dominio>rechazo</dominio>")
    assert registrador.enviados == ["<dominio>tienda</dominio>"]

    fuente = falsos.FuenteLegadaFalsa(["PAGO|P-1,L-1,1,2026-01-01,R"])
    assert fuente.leer_registros() == ["PAGO|P-1,L-1,1,2026-01-01,R"]
