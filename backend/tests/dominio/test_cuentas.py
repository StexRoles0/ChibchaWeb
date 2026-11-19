"""Cuentas y perfiles: RN-05 a RN-13 y RN-15."""

from datetime import date, datetime

import pytest
from freezegun import freeze_time

from chibchaweb.dominio._comun import ZONA
from chibchaweb.dominio.cuentas import (
    CuentaAcceso,
    Direccion,
    Distribuidor,
    Franquicia,
    MedioPago,
    Rol,
    TarjetaCredito,
    Usuario,
)
from chibchaweb.dominio.errores import EstadoInvalidoError, NoEncontradoError, ReglaNegocioError, ValidacionError
from chibchaweb.dominio.facturacion import CategoriaBasica, CategoriaPremium
from chibchaweb.dominio.integraciones import IdentidadExterna
from tests.dominio.conftest import VISA_OK, VISA_RECHAZADA_VALIDADOR
from tests.falsos import ValidadorMedioPagoFalso

# --- Usuario (abstracta) --------------------------------------------------------------------------


def test_usuario_y_medio_pago_son_abstractas():
    with pytest.raises(TypeError):
        Usuario("Ana", "ana@x.co", "1")  # type: ignore[abstract]
    with pytest.raises(TypeError):
        MedioPago()  # type: ignore[abstract]


def test_usuario_valida_sus_datos(nuevo_cliente):
    with pytest.raises(ValidacionError) as e:
        nuevo_cliente(nombre="  ")
    assert e.value.campo == "nombre"
    with pytest.raises(ValidacionError) as e:
        nuevo_cliente(correo="sin-arroba")
    assert e.value.campo == "correo"
    c = nuevo_cliente()
    with pytest.raises(ValidacionError) as e:
        c.telefono = "300-abc"
    assert e.value.campo == "telefono"


def test_usuario_fechas_no_futuras_y_coherentes(nuevo_cliente):
    with pytest.raises(ValidacionError):
        nuevo_cliente(fecha_registro=datetime(2999, 1, 1, tzinfo=ZONA))
    with pytest.raises(ValidacionError):
        nuevo_cliente(
            fecha_registro=datetime(2026, 1, 2, tzinfo=ZONA), fecha_modificacion=datetime(2026, 1, 1, tzinfo=ZONA)
        )


def test_setters_actualizan_fecha_modificacion(nuevo_cliente):
    with freeze_time("2026-01-01 15:00:00"):
        c = nuevo_cliente()
    with freeze_time("2026-02-01 15:00:00"):
        c.nombre = "Laura G."
        c.telefono = "3001234567"
    assert c.nombre == "Laura G." and c.telefono == "3001234567"
    assert c.fecha_modificacion > c.fecha_registro


def test_id_se_asigna_una_sola_vez(nuevo_cliente):
    c = nuevo_cliente()
    assert c.id is None
    c.id = 5
    c.id = 5  # idempotente
    with pytest.raises(ValidacionError):
        c.id = 6
    with pytest.raises(ValidacionError):
        nuevo_cliente().id = 0


# --- RN-05 correo -----------------------------------------------------------------------------


def test_rn05_cliente_no_puede_cambiar_su_correo(cliente):
    with pytest.raises(ReglaNegocioError):
        cliente.correo = "otro@correo.co"
    cliente.correo = "LAURA@correo.co "  # mismo correo normalizado: permitido
    assert cliente.correo == "laura@correo.co"


def test_rn05_empleado_si_puede_cambiar_correo(empleado_soporte):
    empleado_soporte.correo = "nuevo@chibchaweb.co"
    assert empleado_soporte.correo == "nuevo@chibchaweb.co"


# --- RN-06 vincular cuenta ----------------------------------------------------------------------


def test_rn06_vincular_cuenta_crea_cuenta_de_acceso(cliente):
    cliente.vincular_cuenta(IdentidadExterna("10987654321", "Laura", "laura@correo.co", True))
    assert isinstance(cliente.cuenta, CuentaAcceso)
    assert cliente.cuenta.titular is cliente
    assert cliente.cuenta.proveedor == "Google"
    assert cliente.cuenta.coincide_con("10987654321")


def test_rn06_vincular_falla_si_ya_tiene_cuenta(cliente):
    identidad = IdentidadExterna("dev|laura@correo.co", "Laura", "laura@correo.co", True)
    cliente.vincular_cuenta(identidad)
    assert cliente.cuenta.proveedor == "dev"
    with pytest.raises(ReglaNegocioError):
        cliente.vincular_cuenta(identidad)


def test_rn06_distribuidor_no_es_autenticable_ni_vincula(distribuidor):
    assert distribuidor.es_autenticable() is False
    with pytest.raises(ReglaNegocioError):
        distribuidor.vincular_cuenta(IdentidadExterna("x", "A", "a@b.co", True))
    assert distribuidor.cuenta is None


def test_rn06_cliente_y_empleado_son_autenticables(cliente, empleado_soporte):
    assert cliente.es_autenticable() and empleado_soporte.es_autenticable()


# --- RN-07 / RN-08 identidad --------------------------------------------------------------------


def test_rn07_solo_correo_verificado_permite_prellenar_y_vincular_por_correo():
    assert IdentidadExterna("s1", "Ana", "Ana@X.co", True).puede_prellenar_registro() is True
    sin_verificar = IdentidadExterna("s2", "Ana", "ana@x.co", False)
    assert sin_verificar.puede_prellenar_registro() is False
    assert sin_verificar.correo == "ana@x.co"
    assert "ana@x.co" not in repr(sin_verificar) and "s2" not in repr(sin_verificar)


def test_identidad_externa_valida_el_formato_del_correo():
    with pytest.raises(ValidacionError) as e:
        IdentidadExterna("s1", "Ana", "no-es-correo", True)
    assert e.value.campo == "correo"


def test_repr_de_usuario_no_incluye_el_correo(cliente):
    assert cliente.correo not in repr(cliente)


def test_rn07_empleado_sin_cuenta_vincula_en_primer_ingreso(empleado_soporte):
    assert empleado_soporte.cuenta is None
    empleado_soporte.vincular_cuenta(IdentidadExterna("dev|soporte@chibchaweb.co", "S", "soporte@chibchaweb.co", True))
    assert empleado_soporte.cuenta.identificador_externo == "dev|soporte@chibchaweb.co"


def test_rn08_cuenta_se_identifica_por_sub_no_por_correo(cliente):
    cliente.vincular_cuenta(IdentidadExterna("sub-123", "Laura", "laura@correo.co", True))
    assert cliente.cuenta.coincide_con("sub-123")
    assert not cliente.cuenta.coincide_con("laura@correo.co")


def test_rn08_identidad_exige_sub():
    with pytest.raises(ValidacionError):
        IdentidadExterna("", "Ana", "ana@x.co", True)


@freeze_time("2026-11-16 15:00:00")
def test_cuenta_registra_ultimo_acceso(cliente):
    cliente.vincular_cuenta(IdentidadExterna("sub", "L", "laura@correo.co", True))
    assert cliente.cuenta.ultimo_acceso is None
    cliente.cuenta.registrar_acceso()
    assert cliente.cuenta.ultimo_acceso == datetime(2026, 11, 16, 10, 0, tzinfo=ZONA)
    assert cliente.cuenta.fecha_vinculacion is not None and "CuentaAcceso" in repr(cliente.cuenta)


def test_cuenta_exige_titular():
    with pytest.raises(ValidacionError):
        CuentaAcceso("sub", "Google", None)  # type: ignore[arg-type]


# --- RN-09 bajas lógicas ------------------------------------------------------------------------


def test_rn09_inactivar_es_baja_logica(cliente):
    cliente.inactivar()
    assert cliente.activo is False


def test_rn09_eliminar_perfil_suspende_suscripciones(cliente, nueva_suscripcion):
    s1 = nueva_suscripcion(cliente, sitio="uno", id=1)
    s2 = nueva_suscripcion(cliente, sitio="dos", id=2)
    for s in list(cliente.suscripciones):
        cliente.cancelar_suscripcion(s)
    cliente.inactivar()
    assert cliente.suscripciones == ()
    assert not s1.activa and not s2.activa


def test_rn09_cancelar_suscripcion_ajena_falla(cliente, nuevo_cliente, nueva_suscripcion):
    ajena = nueva_suscripcion(nuevo_cliente(correo="otro@x.co", id=11), id=99)
    with pytest.raises(NoEncontradoError):
        cliente.cancelar_suscripcion(ajena)


def test_agregar_suscripcion_de_otro_titular_falla_y_no_duplica(cliente, nuevo_cliente, nueva_suscripcion):
    propia = nueva_suscripcion(cliente, id=1)
    cliente.agregar_suscripcion(propia)
    assert len(cliente.suscripciones) == 1
    ajena = nueva_suscripcion(nuevo_cliente(correo="otro@x.co", id=11), id=2)
    with pytest.raises(ReglaNegocioError):
        cliente.agregar_suscripcion(ajena)


# --- RN-10 datos de facturación -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("direccion", "valida"),
    [
        (Direccion("Calle 1", "Bogotá", "110111"), True),
        (Direccion("Calle 1", "Bogotá", "AB12"), True),
        (Direccion("", "Bogotá", "110111"), False),
        (Direccion("Calle 1", " ", "110111"), False),
        (Direccion("Calle 1", "Bogotá", "123"), False),  # menos de 4
        (Direccion("Calle 1", "Bogotá", "12345678901"), False),  # más de 10
        (Direccion("Calle 1", "Bogotá", "11-011"), False),  # no alfanumérico
        (Direccion("Calle 1", "Bogotá", "110111", pais=""), False),
    ],
)
def test_rn10_direccion_validar(direccion, valida):
    assert direccion.validar() is valida


def test_rn10_direccion_pais_por_defecto_colombia():
    d = Direccion("Calle 1", "Bogotá", "110111")
    assert d.pais == "Colombia" and d.linea == "Calle 1" and d.ciudad == "Bogotá" and d.codigo_postal == "110111"
    assert "Bogotá" in repr(d)


@freeze_time("2026-11-16 15:00:00")
def test_rn10_validar_datos_facturacion_valida_direcciones_y_tarjeta(cliente):
    validador = ValidadorMedioPagoFalso()
    assert cliente.validar_datos_facturacion(validador) is True
    assert validador.verificados == [cliente.medio_pago]


@freeze_time("2026-11-16 15:00:00")
def test_rn10_direccion_invalida_falla_antes_de_la_tarjeta(nuevo_cliente):
    c = nuevo_cliente()
    c.residencia = Direccion("Calle 1", "Bogotá", "1")
    validador = ValidadorMedioPagoFalso()
    with pytest.raises(ValidacionError) as e:
        c.validar_datos_facturacion(validador)
    assert e.value.campo == "residencia"
    assert validador.verificados == []
    c.residencia = Direccion("Calle 1", "Bogotá", "110111")
    c.facturacion = Direccion("", "Bogotá", "110111")
    with pytest.raises(ValidacionError) as e:
        c.validar_datos_facturacion(validador)
    assert e.value.campo == "facturacion"


def test_rn10_cliente_exige_dos_direcciones_distintas_y_medio(nueva_tarjeta, cliente):
    d = Direccion("Calle 1", "Bogotá", "110111")
    from chibchaweb.dominio.cuentas import Cliente

    with pytest.raises(ValidacionError) as e:
        Cliente("A", "a@b.co", "1", d, d, nueva_tarjeta())
    assert e.value.campo == "facturacion"
    with pytest.raises(ValidacionError):
        Cliente("A", "a@b.co", "1", None, d, nueva_tarjeta())  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        Cliente("A", "a@b.co", "1", d, None, nueva_tarjeta())  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        Cliente("A", "a@b.co", "1", d, Direccion("x", "y", "1234"), None)  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        cliente.facturacion = cliente.residencia
    with pytest.raises(ValidacionError):
        cliente.medio_pago = None  # type: ignore[assignment]
    nueva = nueva_tarjeta(numero="4111111111111111")
    cliente.medio_pago = nueva
    assert cliente.medio_pago is nueva


# --- RN-11 tarjeta ----------------------------------------------------------------------------


@freeze_time("2026-11-16 15:00:00")
def test_rn11_tarjeta_valida(nueva_tarjeta):
    assert nueva_tarjeta().validar(ValidadorMedioPagoFalso()) is True


@freeze_time("2026-11-16 15:00:00")
def test_rn11a_numero_debe_cumplir_patron_de_franquicia(nueva_tarjeta):
    with pytest.raises(ValidacionError) as e:
        nueva_tarjeta(numero="5555555555554444").validar(ValidadorMedioPagoFalso())
    assert e.value.campo == "numeroTarjeta"


@freeze_time("2026-11-16 15:00:00")
def test_rn11b_tarjeta_vencida_falla_y_mes_actual_es_vigente(nueva_tarjeta):
    with pytest.raises(ValidacionError) as e:
        nueva_tarjeta(vencimiento=date(2026, 10, 1)).validar(ValidadorMedioPagoFalso())
    assert e.value.campo == "vencimiento"
    assert nueva_tarjeta(vencimiento=date(2026, 11, 1)).esta_vigente() is True
    assert nueva_tarjeta(vencimiento=date(2026, 10, 31)).esta_vigente() is False


@freeze_time("2026-11-16 15:00:00")
@pytest.mark.parametrize("codigo", ["12", "12a", "", "12345"])
def test_rn11c_codigo_de_seguridad_invalido(nueva_tarjeta, codigo):
    with pytest.raises(ValidacionError) as e:
        nueva_tarjeta(codigo=codigo).validar(ValidadorMedioPagoFalso())
    assert e.value.campo == "codigoSeguridad"


@freeze_time("2026-11-16 15:00:00")
def test_rn11c_codigo_de_cuatro_digitos_se_acepta_segun_modelo(nueva_tarjeta):
    # El modelo (prioritario) admite 3 o 4 dígitos; RN-11 dice 3 (P-11).
    assert nueva_tarjeta(codigo="1234").validar(ValidadorMedioPagoFalso()) is True


@freeze_time("2026-11-16 15:00:00")
def test_rn11d_rechazo_del_validador_externo(nueva_tarjeta):
    with pytest.raises(ValidacionError) as e:
        nueva_tarjeta(numero=VISA_RECHAZADA_VALIDADOR).validar(ValidadorMedioPagoFalso())
    assert e.value.campo == "numeroTarjeta"


@freeze_time("2026-11-16 15:00:00")
def test_rn11_orden_patron_antes_que_vigencia(nueva_tarjeta):
    with pytest.raises(ValidacionError) as e:
        nueva_tarjeta(numero="5555555555554444", vencimiento=date(2020, 1, 1)).validar(ValidadorMedioPagoFalso())
    assert e.value.campo == "numeroTarjeta"


def test_rn11_formato_basico_del_numero(visa):
    with pytest.raises(ValidacionError):
        TarjetaCredito("1234", date(2030, 1, 1), visa)
    with pytest.raises(ValidacionError):
        TarjetaCredito(VISA_OK, None, visa)  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        TarjetaCredito(VISA_OK, date(2030, 1, 1), None)  # type: ignore[arg-type]
    t = TarjetaCredito("4242 4242-4242 4242", date(2030, 1, 1), visa)
    assert t.numero == VISA_OK and t.vencimiento == date(2030, 1, 1) and t.franquicia is visa


# --- RN-12 seguridad de la tarjeta -------------------------------------------------------------


@freeze_time("2026-11-16 15:00:00")
def test_rn12_codigo_de_seguridad_se_descarta_tras_validar(nueva_tarjeta):
    t = nueva_tarjeta(codigo="987")
    assert t.codigo_seguridad == "987"
    t.validar(ValidadorMedioPagoFalso())
    assert t.codigo_seguridad is None


@freeze_time("2026-11-16 15:00:00")
def test_rn12_codigo_se_descarta_aunque_la_validacion_falle(nueva_tarjeta):
    t = nueva_tarjeta(numero=VISA_RECHAZADA_VALIDADOR, codigo="987")
    with pytest.raises(ValidacionError):
        t.validar(ValidadorMedioPagoFalso())
    assert t.codigo_seguridad is None


def test_rn12_descripcion_enmascarada_y_repr_sin_datos_sensibles(nueva_tarjeta, cliente):
    t = nueva_tarjeta(codigo="987")
    assert t.descripcion() == "VISA •••• 4242"
    for texto in (repr(t), repr(cliente)):
        assert VISA_OK not in texto and "987" not in texto


# --- RN-13 distribuidor que refiere -------------------------------------------------------------


def test_rn13_asociar_distribuidor_y_agregar_referido(cliente, distribuidor):
    cliente.asociar_distribuidor(distribuidor)
    distribuidor.agregar_referido(cliente)
    distribuidor.agregar_referido(cliente)  # sin duplicar
    assert cliente.distribuidor is distribuidor
    assert distribuidor.referidos == (cliente,)
    assert distribuidor.cantidad_referidos() == 1


def test_rn13_distribuidor_inactivo_o_distinto_falla(cliente, distribuidor):
    otro = Distribuidor("Otro", "otro@x.co", "1", "123", "DIS-OTRO01", id=31)
    otro.inactivar()
    with pytest.raises(ReglaNegocioError):
        cliente.asociar_distribuidor(otro)
    cliente.asociar_distribuidor(distribuidor)
    cliente.asociar_distribuidor(distribuidor)  # mismo: permitido
    with pytest.raises(ReglaNegocioError):
        cliente.asociar_distribuidor(Distribuidor("B", "b@x.co", "1", "1", "DIS-BBBBB2", id=32))


# --- RN-15 código del distribuidor --------------------------------------------------------------


@pytest.mark.parametrize("codigo", ["DIS-ANDES1", "DIS-000000", "DIS-A1B2C3"])
def test_rn15_codigo_distribuidor_valido(codigo):
    assert Distribuidor("A", "a@x.co", "1", "1", codigo).codigo == codigo


@pytest.mark.parametrize("codigo", ["DIS-abc123", "DIS-12345", "XYZ-123456", "DIS-1234567", ""])
def test_rn15_codigo_distribuidor_invalido(codigo):
    with pytest.raises(ValidacionError) as e:
        Distribuidor("A", "a@x.co", "1", "1", codigo)
    assert e.value.campo == "codigo"


# --- Distribuidor / Empleado / Rol / Franquicia -------------------------------------------------


def test_rn19_determinar_categoria_recorre_estrategias(distribuidor, nuevo_cliente):
    categorias = [CategoriaBasica(), CategoriaPremium()]
    assert distribuidor.determinar_categoria(categorias).nombre() == "Básico"
    for i in range(101):
        distribuidor.agregar_referido(nuevo_cliente(correo=f"c{i}@x.co", id=100 + i))
    assert distribuidor.cantidad_referidos() == 101
    assert distribuidor.determinar_categoria(categorias).nombre() == "Premium"
    with pytest.raises(ReglaNegocioError):
        distribuidor.determinar_categoria([CategoriaBasica()])
    with pytest.raises(ReglaNegocioError):
        distribuidor.determinar_categoria([])


def test_distribuidor_comisiones_y_documento(distribuidor):
    from chibchaweb.dominio.facturacion import Comision

    c = Comision(date(2026, 11, 1), date(2026, 11, 30), 0, "Básico", "0.10", distribuidor, id=1)
    distribuidor.agregar_comision(c)
    distribuidor.agregar_comision(c)
    assert distribuidor.comisiones == (c,)
    distribuidor.documento = "900-1"
    assert distribuidor.documento == "900-1"
    with pytest.raises(ValidacionError):
        distribuidor.documento = "con espacio"


def test_empleado_rol_y_permisos(empleado_soporte, catalogo):
    assert empleado_soporte.puede_realizar("ATENDER_TICKETS")
    assert not empleado_soporte.puede_realizar("MIGRAR_DATOS")
    empleado_soporte.cambiar_rol(catalogo.buscar_rol(3))
    assert empleado_soporte.rol.nombre == "Administrador"
    assert empleado_soporte.puede_realizar("MIGRAR_DATOS")
    with pytest.raises(ValidacionError):
        empleado_soporte.cambiar_rol(None)  # type: ignore[arg-type]
    empleado_soporte.documento = "E-2000"
    assert empleado_soporte.documento == "E-2000"
    with pytest.raises(ValidacionError):
        empleado_soporte.documento = ""


def test_empleado_exige_rol():
    from chibchaweb.dominio.cuentas import Empleado

    with pytest.raises(ValidacionError):
        Empleado("A", "a@x.co", "1", "E1", None)  # type: ignore[arg-type]


def test_rol_otorgar_revocar_permite():
    rol = Rol("Soporte", operaciones=["ATENDER_TICKETS", "ATENDER_TICKETS"])
    assert rol.operaciones == ("ATENDER_TICKETS",)
    rol.otorgar("REGISTRAR_TICKET")
    rol.otorgar("REGISTRAR_TICKET")
    assert rol.permite("REGISTRAR_TICKET") and len(rol.operaciones) == 2
    rol.revocar("REGISTRAR_TICKET")
    rol.revocar("NO_EXISTE")
    assert not rol.permite("REGISTRAR_TICKET") and rol.nombre == "Soporte" and "Soporte" in repr(rol)


def test_franquicia_reconoce_numero_y_valida_patron(catalogo):
    visa, master, diners = (catalogo.buscar_franquicia(n) for n in ("VISA", "MASTERCARD", "DINERS"))
    assert visa.reconoce_numero(VISA_OK) and not visa.reconoce_numero("5555555555554444")
    assert master.reconoce_numero("5555555555554444") and master.reconoce_numero("2221000000000009")
    assert diners.reconoce_numero("30569309025904") and not diners.reconoce_numero(VISA_OK)
    assert visa.patron_numero.startswith("^4") and "VISA" in repr(visa)
    with pytest.raises(ValidacionError):
        Franquicia("MALA", "([")


def test_b7_la_cuenta_pasada_al_constructor_debe_tener_al_usuario_como_titular(cliente, nuevo_cliente):
    ajena = CuentaAcceso("dev|x", "dev", cliente)
    with pytest.raises(ValidacionError) as e:
        nuevo_cliente(correo="otro@x.co", cuenta=ajena)
    assert e.value.campo == "cuenta"


# --- Un empleado o distribuidor inactivo no se modifica (revisión final, 5) -----------------------------


def test_empleado_inactivo_no_admite_cambios(empleado_soporte, cliente):
    rol = empleado_soporte.rol
    empleado_soporte.inactivar()
    cambios = [
        lambda: setattr(empleado_soporte, "nombre", "Otro"),
        lambda: setattr(empleado_soporte, "correo", "otro@x.co"),
        lambda: setattr(empleado_soporte, "telefono", "123"),
        lambda: setattr(empleado_soporte, "documento", "X-9"),
        lambda: empleado_soporte.cambiar_rol(rol),
    ]
    for cambio in cambios:
        with pytest.raises(EstadoInvalidoError):
            cambio()
    assert empleado_soporte.nombre != "Otro" and empleado_soporte.documento != "X-9"


def test_distribuidor_inactivo_no_admite_cambios(distribuidor):
    distribuidor.inactivar()
    for atributo, valor in (("nombre", "Otro"), ("correo", "otro@x.co"), ("telefono", "123"), ("documento", "X-9")):
        with pytest.raises(EstadoInvalidoError):
            setattr(distribuidor, atributo, valor)
    assert distribuidor.nombre != "Otro"


def test_empleado_y_distribuidor_activos_se_modifican(empleado_soporte, distribuidor):
    empleado_soporte.nombre = "Nuevo"
    distribuidor.telefono = "3000000000"
    assert empleado_soporte.nombre == "Nuevo" and distribuidor.telefono == "3000000000"
