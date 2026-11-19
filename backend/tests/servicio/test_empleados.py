"""CU-EMP-02, CU-EMP-03 y CU-EMP-04: ServicioEmpleados con repositorios en memoria."""

import pytest

from chibchaweb.dominio.cuentas import Empleado
from chibchaweb.dominio.errores import DuplicadoError, EstadoInvalidoError, NoEncontradoError, ValidacionError
from chibchaweb.servicio.dto import EmpleadoDTO


def datos(**cambios) -> EmpleadoDTO:
    base = dict(nombre="Elena Ruiz", documento="E-2001", correo="Elena@Chibchaweb.co", telefono="3005551122", id_rol=2)
    base.update(cambios)
    return EmpleadoDTO(**base)


# --- EMP-02 --------------------------------------------------------------------------------------
def test_crear_empleado_flujo_principal(empleados, usuarios):
    id = empleados.crear_empleado(datos())
    e = usuarios.buscar_por_id(id)
    assert isinstance(e, Empleado) and e.activo
    assert (e.nombre, e.correo, e.documento, e.rol.nombre) == ("Elena Ruiz", "elena@chibchaweb.co", "E-2001", "Soporte")
    assert e.cuenta is None  # entra después con su cuenta externa (RN-07)


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"nombre": " "}, "nombre"),
        ({"correo": "no-es-correo"}, "correo"),
        ({"telefono": "abc"}, "telefono"),
        ({"documento": "con espacio"}, "documento"),
        ({"id_rol": 99}, "idRol"),
    ],
)
def test_crear_empleado_valida_los_datos(empleados, usuarios, cambios, campo):
    with pytest.raises(ValidacionError) as error:
        empleados.crear_empleado(datos(**cambios))
    assert error.value.campo == campo
    assert usuarios.buscar_empleados("") == []


def test_crear_empleado_con_correo_repetido_es_duplicado(empleados, empleado_gestion):
    with pytest.raises(DuplicadoError) as error:
        empleados.crear_empleado(datos(correo="GESTION@chibchaweb.co"))
    assert error.value.campo == "correo"


def test_crear_empleado_con_correo_de_otro_tipo_de_usuario_es_duplicado(empleados, distribuidor):
    with pytest.raises(DuplicadoError) as error:
        empleados.crear_empleado(datos(correo=distribuidor.correo))
    assert error.value.campo == "correo"


def test_crear_empleado_con_documento_repetido_es_duplicado(empleados, empleado_gestion):
    with pytest.raises(DuplicadoError) as error:
        empleados.crear_empleado(datos(documento="E-1001"))
    assert error.value.campo == "documento"


# --- EMP-03 --------------------------------------------------------------------------------------
def test_modificar_empleado_flujo_principal(empleados, usuarios, empleado_soporte):
    empleados.modificar_empleado(
        empleado_soporte.id, datos(nombre="Sergio S.", documento="E-1009", correo="nuevo@chibchaweb.co", id_rol=1)
    )
    e = usuarios.buscar_por_id(empleado_soporte.id)
    assert (e.nombre, e.documento, e.correo, e.rol.nombre) == ("Sergio S.", "E-1009", "nuevo@chibchaweb.co", "Gestión")


def test_modificar_empleado_sin_cambiar_correo_ni_documento_no_es_duplicado(empleados, empleado_soporte):
    empleados.modificar_empleado(
        empleado_soporte.id, datos(correo="soporte@chibchaweb.co", documento="E-1002", telefono="3009990000")
    )


def test_modificar_empleado_no_deja_cambios_a_medias_si_algo_falla(empleados, usuarios, empleado_soporte):
    with pytest.raises(ValidacionError):
        empleados.modificar_empleado(empleado_soporte.id, datos(nombre="Otro", telefono="xx"))
    assert usuarios.buscar_por_id(empleado_soporte.id).nombre == "Sergio Soporte"


def test_modificar_empleado_con_correo_o_documento_de_otro_es_duplicado(empleados, empleado_soporte, empleado_gestion):
    with pytest.raises(DuplicadoError) as correo:
        empleados.modificar_empleado(empleado_soporte.id, datos(correo=empleado_gestion.correo))
    with pytest.raises(DuplicadoError) as documento:
        empleados.modificar_empleado(empleado_soporte.id, datos(documento="E-1001"))
    assert (correo.value.campo, documento.value.campo) == ("correo", "documento")


def test_modificar_empleado_con_rol_inexistente_es_422(empleados, empleado_soporte):
    with pytest.raises(ValidacionError) as error:
        empleados.modificar_empleado(empleado_soporte.id, datos(id_rol=99))
    assert error.value.campo == "idRol"


def test_modificar_empleado_inexistente_o_de_otro_tipo_es_404(empleados, distribuidor):
    with pytest.raises(NoEncontradoError):
        empleados.modificar_empleado(999, datos())
    with pytest.raises(NoEncontradoError):
        empleados.modificar_empleado(distribuidor.id, datos())


def test_modificar_empleado_inactivo_es_409(empleados, empleado_soporte):
    empleados.eliminar_empleado(empleado_soporte.id)
    with pytest.raises(EstadoInvalidoError):
        empleados.modificar_empleado(empleado_soporte.id, datos())


# --- EMP-04 --------------------------------------------------------------------------------------
def test_eliminar_empleado_es_baja_logica(empleados, usuarios, empleado_soporte):
    empleados.eliminar_empleado(empleado_soporte.id)
    e = usuarios.buscar_por_id(empleado_soporte.id)  # el registro sigue existiendo (RN-09)
    assert e.activo is False


def test_eliminar_empleado_ya_inactivo_es_idempotente(empleados, usuarios, empleado_soporte):
    empleados.eliminar_empleado(empleado_soporte.id)
    modificado = usuarios.buscar_por_id(empleado_soporte.id).fecha_modificacion
    empleados.eliminar_empleado(empleado_soporte.id)
    assert usuarios.buscar_por_id(empleado_soporte.id).fecha_modificacion == modificado


def test_eliminar_empleado_inexistente_o_de_otro_tipo_es_404(empleados, distribuidor):
    with pytest.raises(NoEncontradoError):
        empleados.eliminar_empleado(999)
    with pytest.raises(NoEncontradoError):
        empleados.eliminar_empleado(distribuidor.id)
