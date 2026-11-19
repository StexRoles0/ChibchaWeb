"""Fixtures del servicio: servicios armados con repositorios en memoria y adaptadores falsos."""

import copy
from datetime import date

import pytest

from chibchaweb.dominio.cuentas import Cliente, Direccion, Distribuidor, Empleado, TarjetaCredito
from chibchaweb.dominio.dominios_web import ConstructorXML
from chibchaweb.dominio.facturacion import CategoriaBasica, CategoriaPremium
from chibchaweb.dominio.hospedaje import Plataforma, SitioWeb, Suscripcion
from chibchaweb.dominio.integraciones import IdentidadExterna
from chibchaweb.dominio.migracion import CreadorClienteLegado, CreadorHostingLegado, CreadorPagoLegado
from chibchaweb.dominio.respaldo import (
    ArchivoPlano,
    CifradoAES,
    CifradoCamellia,
    CifradoChaCha20,
    CifradoTwofish,
    GestorContingencia,
)
from chibchaweb.servicio.dto import DatosClienteDTO
from chibchaweb.servicio.servicios import (
    ServicioAcceso,
    ServicioClientes,
    ServicioComisiones,
    ServicioConsultas,
    ServicioContingencia,
    ServicioDistribuidores,
    ServicioDominios,
    ServicioEmpleados,
    ServicioFacturacion,
    ServicioMigracion,
    ServicioSoporte,
)
from tests.falsos import (
    FuenteLegadaFalsa,
    PasarelaPagoFalsa,
    ProveedorAutenticacionFalso,
    RegistradorDominioFalso,
    RepositorioCatalogoEnMemoria,
    RepositorioComisionEnMemoria,
    RepositorioMigracionEnMemoria,
    RepositorioSolicitudDominioEnMemoria,
    RepositorioSuscripcionEnMemoria,
    RepositorioTicketEnMemoria,
    RepositorioUsuarioEnMemoria,
    UnidadDeTrabajoEnMemoria,
    ValidadorMedioPagoFalso,
)


@pytest.fixture
def usuarios():
    return RepositorioUsuarioEnMemoria()


@pytest.fixture
def suscripciones():
    return RepositorioSuscripcionEnMemoria()


@pytest.fixture
def catalogo():
    return RepositorioCatalogoEnMemoria()


@pytest.fixture
def tickets():
    return RepositorioTicketEnMemoria()


@pytest.fixture
def validador():
    return ValidadorMedioPagoFalso()


@pytest.fixture
def acceso(usuarios, suscripciones, catalogo, validador):
    return ServicioAcceso(ProveedorAutenticacionFalso(), validador, usuarios, catalogo, suscripciones)


@pytest.fixture
def clientes(usuarios, suscripciones, catalogo, validador):
    return ServicioClientes(validador, usuarios, catalogo, suscripciones)


@pytest.fixture
def consultas(usuarios, tickets):
    return ServicioConsultas(usuarios, tickets)


@pytest.fixture
def empleados(usuarios, catalogo):
    return ServicioEmpleados(usuarios, catalogo)


@pytest.fixture
def distribuidores(usuarios):
    return ServicioDistribuidores(usuarios)


@pytest.fixture
def solicitudes():
    return RepositorioSolicitudDominioEnMemoria()


@pytest.fixture
def registrador():
    return RegistradorDominioFalso()


@pytest.fixture
def dominios(registrador, solicitudes, usuarios):
    return ServicioDominios(ConstructorXML(), registrador, solicitudes, usuarios)


@pytest.fixture
def soporte(consultas, usuarios, tickets, catalogo, suscripciones):
    return ServicioSoporte(consultas, usuarios, tickets, catalogo, suscripciones)


@pytest.fixture
def datos_registro():
    """Cuerpo de un registro válido, ya completado con la identidad de la sesión (P-07)."""

    def crear(**cambios):
        base = dict(
            telefono="3001234567",
            linea_residencia="Calle 10 # 5-20",
            ciudad_residencia="Bogotá",
            codigo_postal_residencia="110111",
            sitio="TiendaLaura",
            plataforma="UNIX",
            id_paquete=2,
            id_plan=3,
            linea_facturacion="Carrera 7 # 40-10",
            ciudad_facturacion="Bogotá",
            codigo_postal_facturacion="110231",
            numero_tarjeta="4242424242424242",
            vencimiento=date(2099, 12, 1),
            codigo_seguridad="123",
            franquicia="VISA",
            nombre="Laura Gómez",
            identificador_externo="dev|laura@correo.co",
            correo="laura@correo.co",
        )
        base.update(cambios)
        return DatosClienteDTO(**base)

    return crear


@pytest.fixture
def cliente_registrado(acceso, usuarios, datos_registro):
    id = acceso.registrarse(datos_registro())
    return usuarios.buscar_por_id(id)


@pytest.fixture
def datos_pago():
    return DatosClienteDTO(
        linea_facturacion="Av. 68 # 10-10",
        ciudad_facturacion="Medellín",
        codigo_postal_facturacion="050001",
        numero_tarjeta="5105105105105100",
        vencimiento=date(2099, 1, 1),
        codigo_seguridad="4567",
        franquicia="MASTERCARD",
    )


@pytest.fixture
def empleado_soporte(usuarios, catalogo):
    e = Empleado("Sergio Soporte", "soporte@chibchaweb.co", "3002223344", "E-1002", catalogo.buscar_rol(2))
    usuarios.insertar(e)
    return e


@pytest.fixture
def empleado_gestion(usuarios, catalogo):
    e = Empleado("Gabriela Gestión", "gestion@chibchaweb.co", "3001112233", "E-1001", catalogo.buscar_rol(1))
    usuarios.insertar(e)
    return e


@pytest.fixture
def distribuidor(usuarios):
    d = Distribuidor("Andes Digital", "contacto@andesdigital.co", "6015556677", "900123456", "DIS-ANDES1")
    usuarios.insertar(d)
    return d


@pytest.fixture
def cliente_suelto(usuarios, suscripciones, catalogo):
    """Cliente con cuenta y una suscripción ya guardados, sin pasar por el servicio de acceso."""
    c = Cliente(
        "Pedro Pérez",
        "pedro@correo.co",
        "3000000000",
        Direccion("Calle 1", "Cali", "760001"),
        Direccion("Calle 2", "Cali", "760002"),
        TarjetaCredito("4111111111111111", date(2099, 1, 1), catalogo.buscar_franquicia("VISA")),
    )
    c.vincular_cuenta(IdentidadExterna("dev|pedro@correo.co", "Pedro", "pedro@correo.co", True))
    s = Suscripcion(
        c,
        SitioWeb("pedro.chibchaweb.com", Plataforma.WINDOWS),
        catalogo.buscar_paquete(1),
        catalogo.buscar_plan(1),
        date(2026, 1, 1),
    )
    c.agregar_suscripcion(s)
    usuarios.insertar(c)
    suscripciones.insertar(s)
    return c


# --- lote 3: FAC, COM, MIG y RT04 ----------------------------------------------------------------
@pytest.fixture
def pasarela():
    return PasarelaPagoFalsa()


@pytest.fixture
def facturacion(pasarela, suscripciones):
    return ServicioFacturacion(pasarela, suscripciones)


@pytest.fixture
def comisiones():
    return RepositorioComisionEnMemoria()


@pytest.fixture
def servicio_comisiones(comisiones, usuarios, suscripciones):
    return ServicioComisiones([CategoriaBasica(), CategoriaPremium()], comisiones, usuarios, suscripciones)


@pytest.fixture
def nuevo_cliente_con_suscripcion(usuarios, suscripciones, catalogo):
    """Fábrica: cliente con tarjeta y una suscripción (ya guardados) con la fecha de corte indicada."""

    def crear(
        correo="pedro@correo.co",
        numero="4111111111111111",
        vencimiento=date(2099, 1, 1),
        corte=date(2026, 12, 1),
        paquete=2,
        plan=3,
        distribuidor=None,
        sitio=None,
    ):
        c = Cliente(
            "Pedro Pérez",
            correo,
            "3000000000",
            Direccion("Calle 1", "Cali", "760001"),
            Direccion("Calle 2", "Cali", "760002"),
            TarjetaCredito(numero, vencimiento, catalogo.buscar_franquicia("VISA")),
        )
        if distribuidor is not None:
            c.asociar_distribuidor(distribuidor)
            distribuidor.agregar_referido(c)
        s = Suscripcion(
            c,
            SitioWeb(sitio or f"{correo.split('@')[0]}.chibchaweb.com", Plataforma.UNIX),
            catalogo.buscar_paquete(paquete),
            catalogo.buscar_plan(plan),
            date(2026, 6, 1),
            fecha_corte=corte,
        )
        c.agregar_suscripcion(s)
        usuarios.insertar(c)
        suscripciones.insertar(s)
        return s

    return crear


@pytest.fixture
def fuente():
    return FuenteLegadaFalsa()


@pytest.fixture
def creadores(catalogo):
    return [
        CreadorClienteLegado(catalogo.listar_franquicias()),
        CreadorHostingLegado(catalogo.listar_paquetes(), catalogo.listar_planes()),
        CreadorPagoLegado(),
    ]


class _MigracionesQueCopian(RepositorioMigracionEnMemoria):
    """Como un mapeador real: lo guardado y lo que se carga son objetos distintos del que se está usando."""

    def insertar(self, objeto):
        id = super().insertar(objeto)
        self.objetos[id] = copy.deepcopy(objeto)
        return id

    def actualizar(self, objeto):
        super().actualizar(objeto)
        self.objetos[objeto.id] = copy.deepcopy(objeto)

    def buscar_por_id(self, id):
        return copy.deepcopy(super().buscar_por_id(id))


@pytest.fixture
def migraciones():
    return _MigracionesQueCopian()


@pytest.fixture
def unidad():
    return UnidadDeTrabajoEnMemoria()


@pytest.fixture
def migracion(fuente, creadores, migraciones, usuarios, suscripciones, catalogo, unidad):
    return ServicioMigracion(fuente, creadores, migraciones, usuarios, suscripciones, catalogo, unidad)


@pytest.fixture
def gestor(tmp_path):
    clave = bytes(range(32))
    algoritmos = [CifradoAES(clave), CifradoChaCha20(clave), CifradoCamellia(clave), CifradoTwofish(clave)]
    return GestorContingencia(algoritmos, "AES", ArchivoPlano(str(tmp_path / "respaldo.log")))


@pytest.fixture
def contingencia(gestor, usuarios, suscripciones, comisiones, solicitudes, unidad):
    return ServicioContingencia(gestor, usuarios, suscripciones, comisiones, solicitudes, unidad)
