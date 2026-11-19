"""Fábricas de objetos del dominio para las pruebas unitarias (sin BD ni Django)."""

from datetime import date

import pytest

from chibchaweb.dominio.cuentas import Cliente, Direccion, Distribuidor, Empleado, TarjetaCredito
from chibchaweb.dominio.hospedaje import Plataforma, SitioWeb, Suscripcion
from tests import falsos

VISA_OK = "4242424242424242"
VISA_RECHAZADA_VALIDADOR = "4000000000000002"  # termina en 0002 (D-06)
VISA_RECHAZADA_PASARELA = "4000000000000341"  # termina en 0341 (D-06)


@pytest.fixture
def catalogo():
    return falsos.RepositorioCatalogoEnMemoria()


@pytest.fixture
def visa(catalogo):
    return catalogo.buscar_franquicia("VISA")


@pytest.fixture
def nueva_tarjeta(visa):
    def crear(numero=VISA_OK, vencimiento=date(2030, 12, 1), codigo="123"):
        return TarjetaCredito(numero, vencimiento, visa, codigo)

    return crear


@pytest.fixture
def nuevo_cliente(nueva_tarjeta):
    def crear(correo="laura@correo.co", tarjeta=None, id=None, **kwargs):
        return Cliente(
            nombre=kwargs.pop("nombre", "Laura Gómez"),
            correo=correo,
            telefono="300 123 4567",
            residencia=Direccion("Calle 10 # 5-20", "Bogotá", "110111"),
            facturacion=Direccion("Carrera 7 # 40-10", "Bogotá", "110231"),
            medio_pago=tarjeta or nueva_tarjeta(),
            id=id,
            **kwargs,
        )

    return crear


@pytest.fixture
def cliente(nuevo_cliente):
    return nuevo_cliente(id=10)


@pytest.fixture
def nueva_suscripcion(catalogo):
    def crear(titular, paquete_id=2, plan_id=3, fecha_inicio=date(2026, 11, 16), sitio="tiendalaura", id=None):
        s = Suscripcion(
            titular,
            SitioWeb(f"{sitio}.chibchaweb.co", Plataforma.UNIX),
            catalogo.buscar_paquete(paquete_id),
            catalogo.buscar_plan(plan_id),
            fecha_inicio,
            id=id,
        )
        titular.agregar_suscripcion(s)
        return s

    return crear


@pytest.fixture
def nuevo_empleado(catalogo):
    def crear(rol_id=2, correo="soporte@chibchaweb.co", id=None):
        return Empleado("Sergio Soporte", correo, "3002223344", "E-1002", catalogo.buscar_rol(rol_id), id=id)

    return crear


@pytest.fixture
def empleado_soporte(nuevo_empleado):
    return nuevo_empleado(rol_id=2, id=20)


@pytest.fixture
def distribuidor():
    return Distribuidor("Andes Digital SAS", "contacto@andesdigital.co", "6015556677", "900123456", "DIS-ANDES1", id=30)
