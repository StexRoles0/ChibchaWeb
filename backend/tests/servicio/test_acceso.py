"""CU-AUTH-02, CU-AUTH-03 y catálogo: ServicioAcceso con repositorios en memoria."""

from datetime import date

import pytest

from chibchaweb.dominio.cuentas import Cliente
from chibchaweb.dominio.errores import (
    AutorizacionFallidaError,
    DuplicadoError,
    ErrorDominio,
    UsuarioInactivoError,
    ValidacionError,
)
from chibchaweb.dominio.integraciones import IdentidadExterna
from chibchaweb.servicio.dto import ResultadoAccesoDTO


# --- CU-AUTH-02 ----------------------------------------------------------------------------------
def test_login_de_cliente_registrado_por_sub(acceso, cliente_suelto):
    r = acceso.iniciar_sesion("dev:pedro@correo.co")
    assert r == ResultadoAccesoDTO(
        registrado=True, id_usuario=cliente_suelto.id, nombre="Pedro Pérez", correo="pedro@correo.co",
        tipo_usuario="CLIENTE", rol=None, operaciones=(), identificador_externo=None,
    )  # fmt: skip
    assert cliente_suelto.cuenta.ultimo_acceso is not None


def test_login_de_empleado_trae_rol_y_operaciones(acceso, empleado_soporte):
    acceso.iniciar_sesion("dev:soporte@chibchaweb.co")  # primer ingreso: vincula
    r = acceso.iniciar_sesion("dev:soporte@chibchaweb.co")
    assert (r.tipo_usuario, r.rol) == ("EMPLEADO", "Soporte")
    assert set(r.operaciones) == {"ATENDER_TICKETS", "REGISTRAR_TICKET"}


def test_rn07_fa1_primer_ingreso_vincula_por_correo_verificado(acceso, empleado_gestion):
    assert empleado_gestion.cuenta is None
    r = acceso.iniciar_sesion("dev:gestion@chibchaweb.co")
    assert r.registrado and r.rol == "Gestión"
    assert empleado_gestion.cuenta.identificador_externo == "dev|gestion@chibchaweb.co"
    assert empleado_gestion.cuenta.ultimo_acceso is not None


def test_rn07_correo_no_verificado_no_vincula(acceso, empleado_gestion):
    r = acceso.iniciar_sesion("dev-noverificado:gestion@chibchaweb.co")
    assert not r.registrado and r.identificador_externo == "dev|gestion@chibchaweb.co"
    assert empleado_gestion.cuenta is None


def test_fa2_usuario_nuevo_devuelve_datos_para_el_registro(acceso, usuarios):
    r = acceso.iniciar_sesion("dev:laura.gomez@correo.co")
    assert r.registrado is False and r.id_usuario is None
    assert (r.nombre, r.correo, r.tipo_usuario) == ("Laura Gomez", "laura.gomez@correo.co", "")
    assert r.identificador_externo == "dev|laura.gomez@correo.co"
    assert r.operaciones == ()
    assert not usuarios.objetos


def test_distribuidor_no_es_autenticable_y_se_trata_como_no_registrado(acceso, distribuidor):
    r = acceso.iniciar_sesion("dev:contacto@andesdigital.co")
    assert not r.registrado and distribuidor.cuenta is None


def test_fa3_usuario_inactivo(acceso, cliente_suelto, usuarios):
    cliente_suelto.inactivar()
    with pytest.raises(UsuarioInactivoError):
        acceso.iniciar_sesion("dev:pedro@correo.co")


def test_fa3_usuario_inactivo_sin_cuenta_no_se_vincula(acceso, empleado_gestion):
    empleado_gestion.inactivar()
    with pytest.raises(UsuarioInactivoError):
        acceso.iniciar_sesion("dev:gestion@chibchaweb.co")
    assert empleado_gestion.cuenta is None


def test_fa3_codigo_invalido_es_error_de_dominio_generico(acceso):
    with pytest.raises(AutorizacionFallidaError):  # la web lo traduce a 401 AUTORIZACION_FALLIDA (P-19)
        acceso.iniciar_sesion("codigo-malo")


def test_rn08_cuenta_ya_vinculada_a_otro_sub_no_se_reasigna(acceso, cliente_suelto):
    class Otro:
        def autorizar(self, codigo):
            return IdentidadExterna("dev|otro-sub", "Pedro", "pedro@correo.co", True)

    acceso._proveedor = Otro()
    with pytest.raises(ErrorDominio, match="ya tiene una cuenta"):
        acceso.iniciar_sesion("x")


# --- CU-AUTH-03 ----------------------------------------------------------------------------------
def test_registro_crea_cliente_sitio_y_suscripcion(acceso, usuarios, suscripciones, validador, datos_registro):
    id = acceso.registrarse(datos_registro())
    cliente = usuarios.buscar_por_id(id)
    assert isinstance(cliente, Cliente) and cliente.correo == "laura@correo.co" and cliente.nombre == "Laura Gómez"
    assert cliente.cuenta.identificador_externo == "dev|laura@correo.co"
    assert cliente.residencia.pais == "Colombia" and cliente.medio_pago.descripcion() == "VISA •••• 4242"
    (s,) = suscripciones.objetos.values()
    assert s.sitio.subdominio == "tiendalaura.chibchaweb.com" and s.sitio.plataforma.value == "UNIX"  # RN-14, P-15
    assert s.fecha_corte == s.fecha_inicio  # RN-04
    assert s.monto_del_periodo() == 54  # Oro + Semestral, RN-01
    assert len(validador.verificados) == 1  # RN-10
    assert cliente.medio_pago.codigo_seguridad is None  # RN-12


def test_registro_con_codigo_de_distribuidor_lo_asocia_rn13(acceso, usuarios, distribuidor, datos_registro):
    id = acceso.registrarse(datos_registro(codigo_distribuidor="DIS-ANDES1"))
    assert usuarios.buscar_por_id(id).distribuidor is distribuidor
    assert distribuidor.cantidad_referidos() == 1


def test_registro_con_codigo_de_distribuidor_inexistente_falla_rn13(acceso, usuarios, datos_registro):
    with pytest.raises(ValidacionError) as e:
        acceso.registrarse(datos_registro(codigo_distribuidor="DIS-NOEXIS"))
    assert e.value.campo == "codigoDistribuidor" and not usuarios.objetos


def test_registro_con_distribuidor_inactivo_se_rechaza(acceso, distribuidor, datos_registro):
    distribuidor.inactivar()
    with pytest.raises(ValidacionError):
        acceso.registrarse(datos_registro(codigo_distribuidor="DIS-ANDES1"))


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"numero_tarjeta": "4242424242420002"}, "numeroTarjeta"),  # el validador externo la rechaza (D-06)
        ({"numero_tarjeta": "5105105105105100"}, "numeroTarjeta"),  # no es VISA (RN-11 a)
        ({"vencimiento": date(2020, 1, 1)}, "vencimiento"),  # RN-11 b
        ({"vencimiento": None}, "vencimiento"),
        ({"codigo_seguridad": "12"}, "codigoSeguridad"),  # RN-11 c / P-11
        ({"codigo_seguridad": None}, "codigoSeguridad"),
        ({"franquicia": "AMEX"}, "franquicia"),
        ({"id_paquete": 99}, "idPaquete"),
        ({"id_paquete": None}, "idPaquete"),
        ({"id_plan": 99}, "idPlan"),
        ({"plataforma": "MAC"}, "plataforma"),
        ({"plataforma": None}, "plataforma"),
        ({"sitio": "no valido!"}, "sitio"),
        ({"sitio": ""}, "sitio"),
        ({"linea_residencia": ""}, "lineaResidencia"),  # RN-10
        ({"codigo_postal_residencia": "1"}, "lineaResidencia"),
        ({"codigo_postal_facturacion": ""}, "lineaFacturacion"),
        ({"nombre": ""}, "nombre"),
        ({"telefono": "abc"}, "telefono"),
        ({"identificador_externo": None}, "correo"),
        ({"correo": None}, "correo"),
    ],
)
def test_registro_con_datos_invalidos_no_guarda_nada(acceso, usuarios, suscripciones, datos_registro, cambios, campo):
    with pytest.raises(ValidacionError) as e:
        acceso.registrarse(datos_registro(**cambios))
    assert e.value.campo == campo
    assert not usuarios.objetos and not suscripciones.objetos


def test_registro_acepta_codigo_de_seguridad_de_4_digitos(acceso, datos_registro):
    assert acceso.registrarse(datos_registro(codigo_seguridad="1234")) > 0  # P-11


def test_registro_con_subdominio_completo_no_duplica_el_sufijo(acceso, suscripciones, datos_registro):
    acceso.registrarse(datos_registro(sitio="tienda.chibchaweb.com"))
    (s,) = suscripciones.objetos.values()
    assert s.sitio.subdominio == "tienda.chibchaweb.com"


def test_registro_duplicado_se_propaga(acceso, usuarios, datos_registro):
    usuarios.fallar_con = DuplicadoError("correo", "Ya existe")
    with pytest.raises(DuplicadoError):
        acceso.registrarse(datos_registro())


# --- catálogo ------------------------------------------------------------------------------------
def test_catalogo_de_paquetes_y_planes(acceso):
    assert [(p.titulo, p.subtitulo) for p in acceso.consultar_paquetes()] == [
        ("Chibcha-Plata", "5.00"),
        ("Chibcha-Oro", "10.00"),
        ("Chibcha-Platino", "20.00"),
    ]
    assert [p.subtitulo for p in acceso.consultar_planes()] == ["1|0.00", "3|0.05", "6|0.10", "12|0.15"]


def test_catalogo_de_roles(empleados):
    assert [r.titulo for r in empleados.consultar_roles()] == ["Gestión", "Soporte", "Administrador"]


# --- verificar_usuario_activo (P-25): las sesiones de un empleado dado de baja dejan de servir -----
def test_verificar_usuario_activo_deja_pasar_a_un_activo_y_devuelve_su_acceso_actual(
    acceso, empleado_gestion, catalogo
):
    actual = acceso.verificar_usuario_activo(empleado_gestion.id)
    assert actual.registrado and actual.rol == "Gestión" and "GESTIONAR_EMPLEADOS" in actual.operaciones
    empleado_gestion.cambiar_rol(catalogo.buscar_rol(2))  # S-3: el cambio de cargo se ve de inmediato
    actual = acceso.verificar_usuario_activo(empleado_gestion.id)
    assert actual.rol == "Soporte" and "GESTIONAR_EMPLEADOS" not in actual.operaciones
    assert "ATENDER_TICKETS" in actual.operaciones


def test_verificar_usuario_activo_rechaza_al_inactivo_y_al_que_ya_no_existe(acceso, empleado_gestion):
    empleado_gestion.inactivar()
    with pytest.raises(UsuarioInactivoError):
        acceso.verificar_usuario_activo(empleado_gestion.id)
    with pytest.raises(UsuarioInactivoError):
        acceso.verificar_usuario_activo(999)
