"""P-09 y P-21: jerarquía de excepciones usada por la capa web para el 401 y el 403."""

import pytest

from chibchaweb.dominio import errores


@pytest.mark.parametrize("nombre", ["AutorizacionFallidaError", "UsuarioInactivoError"])
def test_p21_subclases_de_error_dominio(nombre):
    clase = getattr(errores, nombre)
    assert issubclass(clase, errores.ErrorDominio) and clase("mensaje").mensaje == "mensaje"


def test_p21_no_son_subclases_entre_si_ni_de_las_demas():
    for a in (errores.AutorizacionFallidaError, errores.UsuarioInactivoError):
        assert not issubclass(a, (errores.ValidacionError, errores.ReglaNegocioError, errores.NoEncontradoError))
    assert not issubclass(errores.AutorizacionFallidaError, errores.UsuarioInactivoError)
