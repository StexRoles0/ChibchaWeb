"""CU-CLI-02, CU-CLI-03 y consultarSitios: ServicioClientes con repositorios en memoria."""

from datetime import date

import pytest

from chibchaweb.dominio.errores import (
    DuplicadoError,
    EstadoInvalidoError,
    NoEncontradoError,
    UsuarioInactivoError,
    ValidacionError,
)
from chibchaweb.servicio.dto import CategoriaPerfil, DatosClienteDTO

PERSONAL, PAQUETE_PLAN, PAGO = CategoriaPerfil.PERSONAL, CategoriaPerfil.PAQUETE_PLAN, CategoriaPerfil.PAGO


@pytest.fixture
def suscripcion(cliente_registrado):
    return cliente_registrado.suscripciones[0]


# --- CLI-03 PERSONAL -----------------------------------------------------------------------------
def test_modificar_personal_aplica_nombre_telefono_residencia_y_sitio(clientes, cliente_registrado, suscripcion):
    clientes.modificar_perfil(
        cliente_registrado.id,
        PERSONAL,
        DatosClienteDTO(
            nombre="Laura G.",
            telefono="3109998888",
            ciudad_residencia="Medellín",
            sitio="nuevositio",
            plataforma="WINDOWS",
        ),
    )
    assert (cliente_registrado.nombre, cliente_registrado.telefono) == ("Laura G.", "3109998888")
    assert cliente_registrado.residencia.ciudad == "Medellín"
    assert cliente_registrado.residencia.linea == "Calle 10 # 5-20"  # lo no enviado se conserva
    assert (
        suscripcion.sitio.subdominio == "nuevositio.chibchaweb.com" and suscripcion.sitio.plataforma.value == "WINDOWS"
    )


def test_modificar_personal_sin_sitio_no_toca_la_suscripcion(clientes, cliente_registrado, suscripcion):
    clientes.modificar_perfil(cliente_registrado.id, PERSONAL, DatosClienteDTO(telefono="3000000001"))
    assert suscripcion.sitio.subdominio == "tiendalaura.chibchaweb.com"


@pytest.mark.parametrize(
    ("datos", "campo"),
    [
        (DatosClienteDTO(nombre=""), "nombre"),
        (DatosClienteDTO(telefono="abc"), "telefono"),
        (DatosClienteDTO(codigo_postal_residencia="1"), "lineaResidencia"),
        (DatosClienteDTO(sitio="no valido!"), "sitio"),
        (DatosClienteDTO(sitio="ok", plataforma="MAC"), "plataforma"),
    ],
)
def test_modificar_personal_invalido_es_422(clientes, cliente_registrado, datos, campo):
    with pytest.raises(ValidacionError) as e:
        clientes.modificar_perfil(cliente_registrado.id, PERSONAL, datos)
    assert e.value.campo == campo


def test_modificar_personal_con_subdominio_ocupado_se_propaga(clientes, cliente_registrado, suscripciones):
    suscripciones.fallar_con = DuplicadoError("sitio", "ocupado")
    with pytest.raises(DuplicadoError):
        clientes.modificar_perfil(cliente_registrado.id, PERSONAL, DatosClienteDTO(sitio="otro"))


def test_rn05_el_correo_no_se_edita(clientes, cliente_registrado):
    clientes.modificar_perfil(cliente_registrado.id, PERSONAL, DatosClienteDTO(correo="otro@x.co", telefono="1"))
    assert cliente_registrado.correo == "laura@correo.co"  # el DTO de modificación ignora el correo


# --- CLI-03 PAQUETE_PLAN -------------------------------------------------------------------------
def test_modificar_paquete_y_plan_no_mueve_la_fecha_de_corte(clientes, cliente_registrado, suscripcion):
    corte = suscripcion.fecha_corte
    clientes.modificar_perfil(
        cliente_registrado.id,
        PAQUETE_PLAN,
        DatosClienteDTO(id_suscripcion=suscripcion.id, id_paquete=3, id_plan=4),
    )
    assert (suscripcion.paquete.id, suscripcion.plan.id) == (3, 4) and suscripcion.fecha_corte == corte
    assert suscripcion.monto_del_periodo() == 204  # Platino anual: 20 x 12 x 0.85


def test_modificar_solo_el_plan(clientes, cliente_registrado, suscripcion):
    clientes.modificar_perfil(
        cliente_registrado.id, PAQUETE_PLAN, DatosClienteDTO(id_suscripcion=suscripcion.id, id_plan=1)
    )
    assert (suscripcion.paquete.id, suscripcion.plan.id) == (2, 1)


@pytest.mark.parametrize(
    ("datos", "campo"),
    [
        (DatosClienteDTO(id_paquete=3), "idSuscripcion"),
        (DatosClienteDTO(id_suscripcion=1), "idPaquete"),
        (DatosClienteDTO(id_suscripcion=1, id_paquete=99), "idPaquete"),
        (DatosClienteDTO(id_suscripcion=1, id_plan=99), "idPlan"),
    ],
)
def test_paquete_plan_invalido_es_422(clientes, cliente_registrado, datos, campo):
    with pytest.raises(ValidacionError) as e:
        clientes.modificar_perfil(cliente_registrado.id, PAQUETE_PLAN, datos)
    assert e.value.campo == campo


def test_paquete_plan_de_una_suscripcion_ajena_es_404(clientes, cliente_registrado):
    with pytest.raises(NoEncontradoError):
        clientes.modificar_perfil(cliente_registrado.id, PAQUETE_PLAN, DatosClienteDTO(id_suscripcion=999, id_plan=1))


def test_paquete_plan_de_una_suscripcion_suspendida_es_409(clientes, cliente_registrado, suscripcion):
    suscripcion.suspender()
    with pytest.raises(EstadoInvalidoError):
        clientes.modificar_perfil(
            cliente_registrado.id, PAQUETE_PLAN, DatosClienteDTO(id_suscripcion=suscripcion.id, id_plan=1)
        )


# --- CLI-03 PAGO ---------------------------------------------------------------------------------
def test_modificar_pago_revalida_y_reemplaza_direccion_y_tarjeta(clientes, cliente_registrado, datos_pago, validador):
    clientes.modificar_perfil(cliente_registrado.id, PAGO, datos_pago)
    assert cliente_registrado.facturacion.ciudad == "Medellín"
    assert cliente_registrado.medio_pago.descripcion() == "MASTERCARD •••• 5100"
    assert cliente_registrado.medio_pago.codigo_seguridad is None  # RN-12
    assert len(validador.verificados) == 2  # registro + modificación (RN-10)


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"numero_tarjeta": "5105105105100002"}, "numeroTarjeta"),  # validador externo
        ({"numero_tarjeta": "4242424242424242"}, "numeroTarjeta"),  # no es MASTERCARD
        ({"vencimiento": date(2020, 1, 1)}, "vencimiento"),
        ({"codigo_seguridad": "1"}, "codigoSeguridad"),
        ({"codigo_seguridad": None}, "codigoSeguridad"),  # D-22: se reingresa completa
        ({"franquicia": "AMEX"}, "franquicia"),
        ({"linea_facturacion": ""}, "lineaFacturacion"),
        ({"codigo_postal_facturacion": "!"}, "lineaFacturacion"),
    ],
)
def test_modificar_pago_invalido_no_cambia_nada_guardado(
    clientes, usuarios, cliente_registrado, datos_pago, cambios, campo
):
    from dataclasses import replace

    antes = cliente_registrado.medio_pago.descripcion()
    with pytest.raises(ValidacionError) as e:
        clientes.modificar_perfil(cliente_registrado.id, PAGO, replace(datos_pago, **cambios))
    assert e.value.campo == campo
    assert usuarios.buscar_por_id(cliente_registrado.id) is cliente_registrado and antes.startswith("VISA")


# --- comunes -------------------------------------------------------------------------------------
def test_modificar_un_usuario_que_no_es_cliente_es_404(clientes, empleado_soporte):
    with pytest.raises(NoEncontradoError):
        clientes.modificar_perfil(empleado_soporte.id, PERSONAL, DatosClienteDTO(telefono="1"))


def test_modificar_un_cliente_inactivo_es_403(clientes, cliente_registrado):
    cliente_registrado.inactivar()
    with pytest.raises(UsuarioInactivoError):
        clientes.modificar_perfil(cliente_registrado.id, PERSONAL, DatosClienteDTO(telefono="1"))


def test_modificar_un_cliente_inexistente_es_404(clientes):
    with pytest.raises(NoEncontradoError):
        clientes.modificar_perfil(999, PERSONAL, DatosClienteDTO())


# --- CLI-02 --------------------------------------------------------------------------------------
def test_eliminar_perfil_inactiva_y_suspende_las_suscripciones_rn09(clientes, cliente_registrado, suscripcion):
    clientes.eliminar_perfil(cliente_registrado.id)
    assert not cliente_registrado.activo and not suscripcion.activa


def test_eliminar_perfil_es_idempotente(clientes, cliente_registrado, suscripcion):
    clientes.eliminar_perfil(cliente_registrado.id)
    modificado = cliente_registrado.fecha_modificacion
    clientes.eliminar_perfil(cliente_registrado.id)
    assert cliente_registrado.fecha_modificacion == modificado


def test_eliminar_perfil_inexistente_o_ajeno_es_404(clientes, empleado_soporte):
    with pytest.raises(NoEncontradoError):
        clientes.eliminar_perfil(999)
    with pytest.raises(NoEncontradoError):
        clientes.eliminar_perfil(empleado_soporte.id)


# --- consultarSitios (P-06) ----------------------------------------------------------------------
def test_consultar_sitios_lista_los_del_cliente(clientes, cliente_registrado, suscripcion):
    (sitio,) = clientes.consultar_sitios(cliente_registrado.id)
    assert sitio.id == suscripcion.sitio.id and sitio.titulo == "tiendalaura.chibchaweb.com"
    assert sitio.subtitulo == "UNIX · Chibcha-Oro" and sitio.estado == "ACTIVA"


def test_consultar_sitios_de_un_no_cliente_es_404(clientes, empleado_soporte):
    with pytest.raises(NoEncontradoError):
        clientes.consultar_sitios(empleado_soporte.id)
