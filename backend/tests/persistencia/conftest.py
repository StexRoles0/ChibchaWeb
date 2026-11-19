"""Fixtures de persistencia: mapeadores reales contra PostgreSQL (se marca cada prueba con django_db)."""

from datetime import date

import pytest

from chibchaweb.dominio.cuentas import Cliente, Direccion, Distribuidor, TarjetaCredito
from chibchaweb.dominio.hospedaje import Plataforma, SitioWeb, Suscripcion
from chibchaweb.dominio.integraciones import IdentidadExterna
from chibchaweb.dominio.respaldo import (
    ArchivoPlano,
    CifradoAES,
    CifradoCamellia,
    CifradoChaCha20,
    CifradoTwofish,
    GestorContingencia,
)
from chibchaweb.persistencia.mapeadores import (
    MapeadorCatalogo,
    MapeadorComision,
    MapeadorMigracion,
    MapeadorSolicitudDominio,
    MapeadorSuscripcion,
    MapeadorTicket,
    MapeadorUsuario,
)

CLAVE = bytes(range(32))


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/persistencia" in str(item.fspath):
            item.add_marker(pytest.mark.django_db)


@pytest.fixture
def ruta_respaldo(tmp_path):
    return tmp_path / "respaldo" / "respaldo.log"


@pytest.fixture
def gestor(ruta_respaldo):
    algoritmos = [CifradoAES(CLAVE), CifradoChaCha20(CLAVE), CifradoCamellia(CLAVE), CifradoTwofish(CLAVE)]
    return GestorContingencia(algoritmos, "AES", ArchivoPlano(str(ruta_respaldo)))


@pytest.fixture
def catalogo():
    return MapeadorCatalogo()


@pytest.fixture
def usuarios(gestor):
    return MapeadorUsuario(gestor)


@pytest.fixture
def suscripciones(gestor):
    return MapeadorSuscripcion(gestor)


@pytest.fixture
def comisiones(gestor):
    return MapeadorComision(gestor)


@pytest.fixture
def solicitudes(gestor):
    return MapeadorSolicitudDominio(gestor)


@pytest.fixture
def tickets(gestor):
    return MapeadorTicket(gestor)


@pytest.fixture
def migraciones():
    from chibchaweb.dominio.migracion import CreadorClienteLegado, CreadorHostingLegado, CreadorPagoLegado

    catalogo = MapeadorCatalogo()
    return MapeadorMigracion(
        [
            CreadorClienteLegado(catalogo.listar_franquicias()),
            CreadorHostingLegado(catalogo.listar_paquetes(), catalogo.listar_planes()),
            CreadorPagoLegado(),
        ]
    )


# --- fábricas de objetos del dominio -----------------------------------------------------------


@pytest.fixture
def nuevo_cliente(catalogo):
    def crear(correo="laura@correo.co", numero="4242424242424242", distribuidor=None, **kwargs):
        return Cliente(
            nombre=kwargs.pop("nombre", "Laura Gómez"),
            correo=correo,
            telefono="300 123 4567",
            residencia=Direccion("Calle 10 # 5-20", "Bogotá", "110111"),
            facturacion=Direccion("Carrera 7 # 40-10", "Bogotá", "110231"),
            medio_pago=TarjetaCredito(numero, date(2030, 12, 1), catalogo.buscar_franquicia("VISA"), "123"),
            distribuidor=distribuidor,
            **kwargs,
        )

    return crear


@pytest.fixture
def distribuidor(usuarios):
    d = Distribuidor("Andes Digital 2", "otro@andesdigital.co", "6015556678", "900999111", "DIS-TEST01")
    usuarios.insertar(d)
    return d


@pytest.fixture
def empleado_soporte(usuarios):
    return next(e for e in usuarios.buscar_empleados("soporte@"))


@pytest.fixture
def cliente(usuarios, nuevo_cliente):
    c = nuevo_cliente()
    c.vincular_cuenta(IdentidadExterna("dev|laura@correo.co", "Laura", "laura@correo.co", True))
    usuarios.insertar(c)
    return c


@pytest.fixture
def nueva_suscripcion(catalogo):
    def crear(titular, sitio="tiendalaura", paquete=2, plan=3, inicio=date(2026, 11, 16)):
        s = Suscripcion(
            titular,
            SitioWeb(f"{sitio}.chibchaweb.com", Plataforma.UNIX),
            catalogo.buscar_paquete(paquete),
            catalogo.buscar_plan(plan),
            inicio,
        )
        titular.agregar_suscripcion(s)
        return s

    return crear
