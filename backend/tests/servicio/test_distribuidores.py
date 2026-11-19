"""CU-DIS-02, CU-DIS-03 y CU-DIS-04: ServicioDistribuidores con repositorios en memoria."""

import re

import pytest

from chibchaweb.dominio.cuentas import Distribuidor
from chibchaweb.dominio.errores import DuplicadoError, EstadoInvalidoError, NoEncontradoError, ValidacionError
from chibchaweb.servicio.dto import DistribuidorDTO
from chibchaweb.servicio.servicios import distribuidores as modulo


def datos(**cambios) -> DistribuidorDTO:
    base = dict(nombre="Sur Digital", documento="800111222", correo="Contacto@SurDigital.co", telefono="6017778899")
    base.update(cambios)
    return DistribuidorDTO(**base)


# --- DIS-02 --------------------------------------------------------------------------------------
def test_rn15_crear_distribuidor_genera_codigo_con_formato(distribuidores, usuarios):
    id = distribuidores.crear_distribuidor(datos())
    d = usuarios.buscar_por_id(id)
    assert isinstance(d, Distribuidor) and d.activo and d.correo == "contacto@surdigital.co"
    assert re.fullmatch(r"DIS-[A-Z0-9]{6}", d.codigo)
    assert d.cuenta is None and d.es_autenticable() is False


def test_rn15_el_codigo_es_unico_aunque_el_generador_choque(distribuidores, usuarios, distribuidor, monkeypatch):
    codigos = iter(["DIS-ANDES1", "DIS-ANDES1", "DIS-NUEVO2"])  # los dos primeros ya existen
    monkeypatch.setattr(modulo, "_generar_codigo", lambda: next(codigos))
    id = distribuidores.crear_distribuidor(datos())
    assert usuarios.buscar_por_id(id).codigo == "DIS-NUEVO2"


def test_rn15_el_codigo_de_un_distribuidor_inactivo_tampoco_se_reutiliza(
    distribuidores, usuarios, distribuidor, monkeypatch
):
    distribuidor.inactivar()
    codigos = iter(["DIS-ANDES1", "DIS-OTRO99"])
    monkeypatch.setattr(modulo, "_generar_codigo", lambda: next(codigos))
    assert usuarios.buscar_por_id(distribuidores.crear_distribuidor(datos())).codigo == "DIS-OTRO99"


def test_crear_distribuidor_sin_codigo_libre_falla(distribuidores, distribuidor, monkeypatch):
    monkeypatch.setattr(modulo, "_generar_codigo", lambda: "DIS-ANDES1")
    with pytest.raises(DuplicadoError) as error:
        distribuidores.crear_distribuidor(datos())
    assert error.value.campo == "codigo"


def test_crear_distribuidor_reintenta_si_otro_proceso_tomo_el_codigo(distribuidores, usuarios, monkeypatch):
    codigos = iter(["DIS-AAAAAA", "DIS-BBBBBB"])
    monkeypatch.setattr(modulo, "_generar_codigo", lambda: next(codigos))
    original = usuarios.insertar
    llamadas = []

    def insertar(objeto):
        llamadas.append(objeto.codigo)
        if len(llamadas) == 1:
            raise DuplicadoError("codigo", "choque en la BD")
        return original(objeto)

    usuarios.insertar = insertar
    assert usuarios.buscar_por_id(distribuidores.crear_distribuidor(datos())).codigo == "DIS-BBBBBB"
    assert llamadas == ["DIS-AAAAAA", "DIS-BBBBBB"]


def test_crear_distribuidor_no_reintenta_otros_duplicados(distribuidores, usuarios):
    def insertar(objeto):
        raise DuplicadoError("documento", "choque en la BD")

    usuarios.insertar = insertar
    with pytest.raises(DuplicadoError) as error:
        distribuidores.crear_distribuidor(datos())
    assert error.value.campo == "documento"


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"nombre": ""}, "nombre"),
        ({"correo": "x"}, "correo"),
        ({"telefono": "a"}, "telefono"),
        ({"documento": "!"}, "documento"),
    ],
)
def test_crear_distribuidor_valida_los_datos(distribuidores, cambios, campo):
    with pytest.raises(ValidacionError) as error:
        distribuidores.crear_distribuidor(datos(**cambios))
    assert error.value.campo == campo


def test_crear_distribuidor_duplicados(distribuidores, distribuidor, empleado_gestion):
    with pytest.raises(DuplicadoError) as correo:
        distribuidores.crear_distribuidor(datos(correo=distribuidor.correo))
    with pytest.raises(DuplicadoError) as documento:
        distribuidores.crear_distribuidor(datos(documento="900123456"))
    with pytest.raises(DuplicadoError) as otro_tipo:
        distribuidores.crear_distribuidor(datos(correo=empleado_gestion.correo))
    assert (correo.value.campo, documento.value.campo, otro_tipo.value.campo) == ("correo", "documento", "correo")


# --- DIS-03 --------------------------------------------------------------------------------------
def test_modificar_distribuidor_conserva_el_codigo(distribuidores, usuarios, distribuidor):
    distribuidores.modificar_distribuidor(distribuidor.id, datos(documento="900123456"))
    d = usuarios.buscar_por_id(distribuidor.id)
    assert (d.nombre, d.documento, d.correo, d.codigo) == (
        "Sur Digital",
        "900123456",
        "contacto@surdigital.co",
        "DIS-ANDES1",
    )


def test_modificar_distribuidor_duplicado_valida_y_no_deja_cambios_a_medias(distribuidores, usuarios, distribuidor):
    otro = usuarios.buscar_por_id(distribuidores.crear_distribuidor(datos()))
    with pytest.raises(DuplicadoError) as correo:
        distribuidores.modificar_distribuidor(distribuidor.id, datos(correo=otro.correo))
    with pytest.raises(DuplicadoError) as documento:
        distribuidores.modificar_distribuidor(distribuidor.id, datos(documento=otro.documento, correo="x@y.co"))
    with pytest.raises(ValidacionError):
        distribuidores.modificar_distribuidor(distribuidor.id, datos(nombre="Nuevo", telefono="no"))
    assert (correo.value.campo, documento.value.campo) == ("correo", "documento")
    assert usuarios.buscar_por_id(distribuidor.id).nombre == "Andes Digital"


def test_modificar_distribuidor_inexistente_inactivo_u_otro_tipo(distribuidores, empleado_gestion, distribuidor):
    with pytest.raises(NoEncontradoError):
        distribuidores.modificar_distribuidor(999, datos())
    with pytest.raises(NoEncontradoError):
        distribuidores.modificar_distribuidor(empleado_gestion.id, datos())
    distribuidores.eliminar_distribuidor(distribuidor.id)
    with pytest.raises(EstadoInvalidoError):
        distribuidores.modificar_distribuidor(distribuidor.id, datos())


# --- DIS-04 --------------------------------------------------------------------------------------
def test_eliminar_distribuidor_es_baja_logica_e_idempotente(distribuidores, usuarios, distribuidor):
    distribuidores.eliminar_distribuidor(distribuidor.id)
    assert usuarios.buscar_por_id(distribuidor.id).activo is False
    assert usuarios.buscar_distribuidor_por_codigo("DIS-ANDES1") is None  # RN-13: ya no se puede usar
    distribuidores.eliminar_distribuidor(distribuidor.id)  # no falla


def test_eliminar_distribuidor_inexistente_u_otro_tipo(distribuidores, empleado_gestion):
    with pytest.raises(NoEncontradoError):
        distribuidores.eliminar_distribuidor(999)
    with pytest.raises(NoEncontradoError):
        distribuidores.eliminar_distribuidor(empleado_gestion.id)
