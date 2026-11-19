"""MapeadorMigracion: proceso con su log."""

import pytest

from chibchaweb.dominio.errores import NoEncontradoError
from chibchaweb.dominio.migracion import EstadoMigracion, NivelLog, ProcesoMigracion
from tests.falsos import FuenteLegadaFalsa


@pytest.fixture
def administrador(usuarios):
    return usuarios.buscar_empleados("admin@")[0]


@pytest.fixture
def proceso(migraciones, administrador):
    p = ProcesoMigracion(administrador, list(migraciones._creadores))
    migraciones.insertar(p)
    return p


def test_ida_y_vuelta_y_transiciones(migraciones, proceso, administrador):
    leido = migraciones.buscar_por_id(proceso.id)
    assert (
        leido is not proceso and leido.ejecutor.id == administrador.id and leido.ejecutor.rol.nombre == "Administrador"
    )
    assert (leido.estado, leido.fecha_inicio, leido.fecha_fin, leido.log) == (
        EstadoMigracion.CREADA,
        proceso.fecha_inicio,
        None,
        (),
    )
    assert len(leido.creadores) == 3

    fuente = FuenteLegadaFalsa(
        [
            'CLIENTE|C1,Ana,ana@x.co,"Calle 1, Bogotá, 110111",4242424242424242,3001,2030-01-01,VISA',
            "CLIENTE|C2,,malo,,,,,",
            "HOSTING|H1,C1,ana.chibchaweb.com,Chibcha-Oro,Mensual,UNIX",
        ]
    )
    proceso.simular(fuente)
    migraciones.actualizar(proceso)
    migraciones.actualizar(proceso)  # no duplica el log
    proceso.aprobar()
    migraciones.actualizar(proceso)
    recargado = migraciones.buscar_por_id(proceso.id)
    assert recargado.estado is EstadoMigracion.APROBADA and len(recargado.log) == len(proceso.log) == 3
    assert [e.nivel for e in recargado.log] == [NivelLog.INFO, NivelLog.ERROR, NivelLog.INFO]
    assert [(e.tipo_registro, e.identificador_legado) for e in recargado.log] == [
        ("CLIENTE", "C1"),
        ("CLIENTE", "C2"),
        ("HOSTING", "H1"),
    ]
    assert recargado.log[0].fecha == proceso.log[0].fecha and recargado.log[1].mensaje == proceso.log[1].mensaje
    recargado.preparar_ejecucion(fuente)  # los creadores inyectados siguen validando
    proceso.marcar_revertido()
    migraciones.actualizar(proceso)
    assert migraciones.buscar_por_id(proceso.id).estado is EstadoMigracion.REVERTIDA
    assert migraciones.buscar_por_id(proceso.id).fecha_fin == proceso.fecha_fin


def test_filtro_y_no_encontrado(migraciones, proceso):
    assert [p.id for p in migraciones.buscar_por_filtro("creada")] == [proceso.id]
    assert [p.id for p in migraciones.buscar_por_filtro("administra")] == [proceso.id]
    assert migraciones.buscar_por_filtro("ejecutada") == []
    assert migraciones.existe(proceso.id) and not migraciones.existe(999999)
    with pytest.raises(NoEncontradoError):
        migraciones.buscar_por_id(999999)
