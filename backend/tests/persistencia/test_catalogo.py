"""MapeadorCatalogo: lectura de los catálogos de schema.sql y seed_dev.sql."""

from decimal import Decimal

import pytest

from chibchaweb.dominio.errores import NoEncontradoError


def test_paquetes_y_planes(catalogo):
    paquetes = catalogo.listar_paquetes()
    assert [(p.nombre, p.tarifa_mensual) for p in paquetes] == [
        ("Chibcha-Plata", Decimal("5.00")),
        ("Chibcha-Oro", Decimal("10.00")),
        ("Chibcha-Platino", Decimal("20.00")),
    ]
    assert catalogo.buscar_paquete(paquetes[1].id).nombre == "Chibcha-Oro"
    planes = catalogo.listar_planes()
    assert [(p.nombre, p.meses, p.descuento) for p in planes] == [
        ("Mensual", 1, Decimal("0.00")),
        ("Trimestral", 3, Decimal("0.05")),
        ("Semestral", 6, Decimal("0.10")),
        ("Anual", 12, Decimal("0.15")),
    ]
    assert catalogo.buscar_plan(planes[2].id).nombre == "Semestral"
    oro, semestral = catalogo.buscar_paquete(paquetes[1].id), catalogo.buscar_plan(planes[2].id)
    assert oro.calcular_monto(semestral) == Decimal("54.00")  # RN-01
    for consulta in (catalogo.buscar_paquete, catalogo.buscar_plan, catalogo.buscar_rol):
        with pytest.raises(NoEncontradoError):
            consulta(999999)


def test_franquicias(catalogo):
    assert [f.nombre for f in catalogo.listar_franquicias()] == ["VISA", "MASTERCARD", "DINERS"]
    visa = catalogo.buscar_franquicia("visa")
    assert visa.id and visa.reconoce_numero("4242424242424242") and not visa.reconoce_numero("5555555555554444")
    with pytest.raises(NoEncontradoError):
        catalogo.buscar_franquicia("AMEX")


def test_roles_con_operaciones(catalogo):
    roles = catalogo.listar_roles()
    assert [r.nombre for r in roles] == ["Gestión", "Soporte", "Administrador"]
    soporte = next(r for r in roles if r.nombre == "Soporte")
    assert set(soporte.operaciones) == {"ATENDER_TICKETS", "REGISTRAR_TICKET"}
    admin = catalogo.buscar_rol(next(r.id for r in roles if r.nombre == "Administrador"))
    assert (
        admin.permite("MIGRAR_DATOS")
        and admin.permite("GESTIONAR_CONTINGENCIA")
        and not admin.permite("ATENDER_TICKETS")
    )


def test_niveles_de_servicio(catalogo):
    inicial = catalogo.buscar_nivel_inicial()
    assert (inicial.nombre, inicial.orden, inicial.es_ultimo) == ("Soporte", 1, False)
    segundo = catalogo.buscar_nivel_siguiente(inicial)
    assert (segundo.nombre, segundo.orden) == ("Gestión", 2)
    ultimo = catalogo.buscar_nivel_siguiente(segundo)
    assert (ultimo.nombre, ultimo.es_ultimo) == ("Desarrollo", True)
    assert catalogo.buscar_nivel_siguiente(ultimo) is None
