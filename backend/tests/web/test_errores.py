"""``web/errores.py``: tabla de api.md §Errores, incluida la contingencia (503) y la que no tiene BD."""

from unittest import mock

import pytest
from rest_framework import exceptions

from chibchaweb.servicio import errores as e
from chibchaweb.web.errores import manejador, traducir
from config.contenedor import contenedor
from tests.web.conftest import BASE, assert_error

TABLA = [
    (e.ValidacionError("vencimiento", "La tarjeta está vencida"), 422, "VALIDACION", "vencimiento"),
    (e.ReglaNegocioError("regla"), 422, "REGLA_NEGOCIO", None),
    (e.EstadoInvalidoError("estado"), 409, "ESTADO_INVALIDO", None),
    (e.NoEncontradoError("no existe"), 404, "NO_ENCONTRADO", None),
    (e.DuplicadoError("correo", "ya existe"), 409, "DUPLICADO", "correo"),
    (e.DuplicadoError("sitio", "ocupado"), 409, "SUBDOMINIO_EN_USO", "sitio"),
    (e.ContingenciaActivaError("respaldado"), 503, "CONTINGENCIA", None),
    (e.UsuarioInactivoError("inactivo"), 403, "USUARIO_INACTIVO", None),
    (e.AutorizacionFallidaError("rechazado"), 401, "AUTORIZACION_FALLIDA", None),
    (e.ErrorDominio("otro"), 422, "REGLA_NEGOCIO", None),
]


@pytest.mark.parametrize(("excepcion", "estado", "codigo", "campo"), TABLA)
def test_cada_excepcion_del_dominio_tiene_su_codigo_http(excepcion, estado, codigo, campo):
    respuesta = manejador(excepcion, {})
    assert respuesta.status_code == estado
    assert respuesta.data == ({"codigo": codigo, "mensaje": excepcion.mensaje} | ({"campo": campo} if campo else {}))


def test_errores_de_drf_se_traducen():
    assert manejador(exceptions.NotAuthenticated(), {}).data["codigo"] == "NO_AUTENTICADO"
    assert manejador(exceptions.PermissionDenied(), {}).data["codigo"] == "SIN_PERMISO"
    assert manejador(exceptions.ParseError(), {}).data["codigo"] == "SOLICITUD_INVALIDA"
    assert manejador(exceptions.MethodNotAllowed("PUT"), {}).status_code == 405
    assert manejador(exceptions.NotFound(), {}).status_code == 404
    assert manejador(RuntimeError("bug"), {}) is None and traducir(RuntimeError()) is None


def test_la_contingencia_llega_como_503_por_la_vista(gestion):
    with mock.patch.object(
        contenedor().servicio_consultas, "consultar_basico", side_effect=e.ContingenciaActivaError("respaldado")
    ):
        assert_error(gestion.get(f"{BASE}/consultas/CLIENTE"), 503, "CONTINGENCIA")


def test_una_lectura_con_la_bd_caida_llega_como_503(gestion):
    from django.db import OperationalError

    with mock.patch(
        "chibchaweb.persistencia.mapeadores.usuario.UsuarioOrm.objects", new_callable=mock.PropertyMock
    ) as objects:
        objects.side_effect = OperationalError("sin conexión")
        assert_error(gestion.get(f"{BASE}/consultas/CLIENTE"), 503, "CONTINGENCIA")


@pytest.mark.parametrize("error", ["OperationalError", "InterfaceError"])
def test_d30_un_error_de_conexion_sin_mapeador_es_503_contingencia(error):
    """La BD cayó antes de llegar a un mapeador (p. ej. al abrir la transacción de la petición)."""
    from django import db

    estado, cuerpo = traducir(getattr(db, error)("connection refused"))
    assert (estado, cuerpo["codigo"]) == (503, "CONTINGENCIA")
    assert "refused" not in cuerpo["mensaje"]  # no se filtra el texto del driver


class _AtomicQueFallaAlCerrar:
    """Como ``transaction.atomic()`` con la BD caída: entrar funciona y cerrar (reconectar) lanza OperationalError."""

    def __enter__(self):
        return self

    def __exit__(self, *excepcion):
        from django.db import OperationalError

        raise OperationalError("connection refused")


def test_d30_transaccional_conserva_la_excepcion_del_mapeador_si_cerrar_la_transaccion_falla():
    from chibchaweb.web.utilidades import transaccional

    @transaccional
    def vista():
        raise e.ContingenciaActivaError("respaldado")

    with mock.patch("chibchaweb.transaccion.transaction.atomic", _AtomicQueFallaAlCerrar):
        with pytest.raises(e.ContingenciaActivaError, match="respaldado"):
            vista()


def test_d30_transaccional_propaga_la_falla_de_la_bd_si_la_vista_no_fallo():
    from django.db import OperationalError

    from chibchaweb.web.utilidades import transaccional

    @transaccional
    def vista():
        return "ok"

    with mock.patch("chibchaweb.transaccion.transaction.atomic", _AtomicQueFallaAlCerrar):
        with pytest.raises(OperationalError):  # el manejador la traduce a 503
            vista()


@pytest.mark.parametrize("error", ["IntegrityError", "DataError", "ProgrammingError"])
def test_un_error_de_bd_no_previsto_es_500_json_generico_sin_detalles(error, caplog):
    from django.db import utils

    with caplog.at_level("ERROR"):
        respuesta = manejador(getattr(utils, error)('viola la restriccion "secreta_check"'), {})
    assert respuesta.status_code == 500
    assert respuesta.data == {
        "codigo": "ERROR_INTERNO",
        "mensaje": "Ocurrió un error interno; intente de nuevo más tarde",
    }
    assert "secreta_check" not in str(respuesta.data) and "secreta_check" in caplog.text  # solo en el log


def test_un_integrity_error_en_una_vista_responde_500_json(gestion):
    from django.db import IntegrityError

    with mock.patch.object(contenedor().usuarios, "buscar_empleados", side_effect=IntegrityError("x_check")):
        r = gestion.get(f"{BASE}/empleados")
    assert r.status_code == 500 and r.json()["codigo"] == "ERROR_INTERNO" and "x_check" not in r.content.decode()
