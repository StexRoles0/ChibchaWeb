"""UnidadDeTrabajoDjango: confirmar y revertir (P-04, RN-27)."""

import pytest

from chibchaweb.dominio.cuentas import Distribuidor
from chibchaweb.dominio.errores import EstadoInvalidoError
from chibchaweb.persistencia.transacciones import UnidadDeTrabajoDjango


def _nuevo(n):
    return Distribuidor(f"Dist {n}", f"d{n}@x.co", "601", f"90{n}", f"DIS-UOW{n:03d}")


def test_confirmar_conserva_los_cambios(usuarios):
    unidad = UnidadDeTrabajoDjango()
    unidad.iniciar()
    d = _nuevo(1)
    usuarios.insertar(d)
    unidad.confirmar()
    assert usuarios.existe(d.id) and usuarios.buscar_por_correo("d1@x.co") is not None


def test_revertir_descarta_todo_lo_escrito_en_la_unidad(usuarios):
    unidad = UnidadDeTrabajoDjango()
    unidad.iniciar()
    a, b = _nuevo(2), _nuevo(3)
    usuarios.insertar(a)
    usuarios.insertar(b)
    assert usuarios.existe(a.id)
    unidad.revertir()
    assert not usuarios.existe(a.id) and not usuarios.existe(b.id)
    assert usuarios.buscar_por_correo("d2@x.co") is None


def test_revertir_interno_no_afecta_lo_anterior(usuarios):
    externa, interna = UnidadDeTrabajoDjango(), UnidadDeTrabajoDjango()
    externa.iniciar()
    a = _nuevo(4)
    usuarios.insertar(a)
    interna.iniciar()
    b = _nuevo(5)
    usuarios.insertar(b)
    interna.revertir()
    externa.confirmar()
    assert usuarios.existe(a.id) and not usuarios.existe(b.id)


def test_se_puede_seguir_usando_tras_revertir_y_exige_iniciar(usuarios):
    unidad = UnidadDeTrabajoDjango()
    with pytest.raises(EstadoInvalidoError):
        unidad.confirmar()
    with pytest.raises(EstadoInvalidoError):
        unidad.revertir()
    unidad.iniciar()
    unidad.revertir()
    unidad.iniciar()
    d = _nuevo(6)
    usuarios.insertar(d)
    unidad.confirmar()
    assert usuarios.existe(d.id)
