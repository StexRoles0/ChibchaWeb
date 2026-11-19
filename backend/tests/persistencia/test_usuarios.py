"""MapeadorUsuario: ida y vuelta de cada subtipo y cada método del repositorio."""

from datetime import date

import pytest
from django.db import connection

from chibchaweb.dominio.cuentas import Cliente, Distribuidor, Empleado, TarjetaCredito
from chibchaweb.dominio.errores import DuplicadoError, NoEncontradoError
from chibchaweb.dominio.integraciones import IdentidadExterna


def test_cliente_ida_y_vuelta(usuarios, cliente, catalogo):
    assert cliente.id is not None and cliente.residencia.id and cliente.medio_pago.id and cliente.cuenta.id
    leido = usuarios.buscar_por_id(cliente.id)
    assert isinstance(leido, Cliente) and leido is not cliente
    assert (leido.nombre, leido.correo, leido.telefono, leido.activo) == (
        cliente.nombre,
        cliente.correo,
        cliente.telefono,
        True,
    )
    assert leido.fecha_registro == cliente.fecha_registro and leido.fecha_modificacion == cliente.fecha_modificacion
    assert (leido.residencia.linea, leido.residencia.ciudad, leido.residencia.codigo_postal, leido.residencia.pais) == (
        "Calle 10 # 5-20",
        "Bogotá",
        "110111",
        "Colombia",
    )
    assert leido.facturacion.codigo_postal == "110231" and leido.facturacion.id != leido.residencia.id
    tarjeta = leido.medio_pago
    assert isinstance(tarjeta, TarjetaCredito)
    assert tarjeta.numero == "4242424242424242" and tarjeta.vencimiento == date(2030, 12, 1)
    assert tarjeta.franquicia.nombre == "VISA" and tarjeta.codigo_seguridad is None
    assert leido.cuenta.identificador_externo == "dev|laura@correo.co" and leido.cuenta.proveedor == "dev"
    assert leido.cuenta.fecha_vinculacion == cliente.cuenta.fecha_vinculacion and leido.cuenta.titular is leido
    assert leido.distribuidor is None and leido.suscripciones == ()


def test_numero_de_tarjeta_se_guarda_cifrado_y_sin_codigo(usuarios, cliente):
    with connection.cursor() as c:
        c.execute(
            "SELECT numero_cifrado, algoritmo_cifrado, ultimos_digitos FROM tarjeta_credito WHERE id=%s",
            [cliente.medio_pago.id],
        )
        cifrado, algoritmo, ultimos = c.fetchone()
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='tarjeta_credito'")
        columnas = {f[0] for f in c.fetchall()}
    assert "4242424242424242" not in cifrado and algoritmo == "AES" and ultimos == "4242"
    assert not any("codigo" in col or "cvv" in col for col in columnas)


def test_tarjeta_usa_el_algoritmo_activo_y_se_lee_con_el_de_la_fila(usuarios, nuevo_cliente, gestor):
    gestor.cambiar_algoritmo("Camellia")
    c = nuevo_cliente(correo="cam@correo.co")
    usuarios.insertar(c)
    gestor.cambiar_algoritmo("AES")
    with connection.cursor() as cur:
        cur.execute("SELECT algoritmo_cifrado FROM tarjeta_credito WHERE id=%s", [c.medio_pago.id])
        assert cur.fetchone()[0] == "Camellia"
    assert usuarios.buscar_por_id(c.id).medio_pago.numero == "4242424242424242"


def test_cliente_con_distribuidor_y_referidos(usuarios, nuevo_cliente, distribuidor):
    c = nuevo_cliente(correo="ref@correo.co")
    c.asociar_distribuidor(distribuidor)
    distribuidor.agregar_referido(c)
    usuarios.insertar(c)
    leido = usuarios.buscar_por_id(c.id)
    assert leido.distribuidor.id == distribuidor.id and leido.distribuidor.codigo == "DIS-TEST01"
    raiz = usuarios.buscar_distribuidor_por_codigo("DIS-TEST01")
    assert isinstance(raiz, Distribuidor) and raiz.cantidad_referidos() == 1
    assert raiz.referidos[0].id == c.id and raiz.referidos[0].distribuidor is raiz


def test_empleado_y_distribuidor_ida_y_vuelta(usuarios, catalogo, distribuidor):
    rol = catalogo.buscar_rol(2)
    e = Empleado("Nuevo Emp", "nuevo@chibchaweb.co", "3001", "E-9", rol)
    usuarios.insertar(e)
    leido = usuarios.buscar_por_id(e.id)
    assert isinstance(leido, Empleado) and leido.documento == "E-9" and leido.rol.nombre == "Soporte"
    assert leido.puede_realizar("ATENDER_TICKETS") and not leido.puede_realizar("MIGRAR_DATOS")
    d = usuarios.buscar_por_id(distribuidor.id)
    assert isinstance(d, Distribuidor) and (d.documento, d.codigo) == ("900999111", "DIS-TEST01")


def test_actualizar_cliente_cambia_direcciones_tarjeta_y_cuenta(usuarios, cliente, catalogo):
    from chibchaweb.dominio.cuentas import Direccion

    id_residencia, id_medio = cliente.residencia.id, cliente.medio_pago.id
    cliente.nombre = "Laura G."
    cliente.telefono = "3111111111"
    cliente.residencia = Direccion("Av 1 # 2-3", "Medellín", "050001")
    cliente.medio_pago = TarjetaCredito(
        "5555555555554444", date(2031, 1, 1), catalogo.buscar_franquicia("MASTERCARD"), "999"
    )
    cliente.cuenta.registrar_acceso()
    usuarios.actualizar(cliente)
    assert cliente.residencia.id not in (None, id_residencia) and cliente.medio_pago.id not in (None, id_medio)
    leido = usuarios.buscar_por_id(cliente.id)
    assert leido.nombre == "Laura G." and leido.telefono == "3111111111"
    assert leido.residencia.ciudad == "Medellín" and leido.medio_pago.numero == "5555555555554444"
    assert leido.medio_pago.franquicia.nombre == "MASTERCARD"
    assert leido.cuenta.ultimo_acceso == cliente.cuenta.ultimo_acceso
    assert not usuarios.existe(0) and usuarios.existe(cliente.id)
    with connection.cursor() as c:  # lo reemplazado no queda guardado
        c.execute("SELECT count(*) FROM direccion WHERE id=%s", [id_residencia])
        assert c.fetchone()[0] == 0
        c.execute("SELECT count(*) FROM medio_pago WHERE id=%s", [id_medio])
        assert c.fetchone()[0] == 0


def test_actualizar_vincula_cuenta_de_empleado(usuarios, empleado_soporte):
    empleado_soporte.vincular_cuenta(IdentidadExterna("dev|soporte@chibchaweb.co", "S", "soporte@chibchaweb.co", True))
    usuarios.actualizar(empleado_soporte)
    leido = usuarios.buscar_por_id(empleado_soporte.id)
    assert leido.cuenta.identificador_externo == "dev|soporte@chibchaweb.co"


def test_buscar_por_identificador_correo_y_distribuidor(usuarios, cliente, distribuidor):
    assert usuarios.buscar_por_identificador_externo("dev|laura@correo.co").id == cliente.id
    assert usuarios.buscar_por_identificador_externo("no-existe") is None
    assert usuarios.buscar_por_correo(" LAURA@correo.co ").id == cliente.id
    assert usuarios.buscar_por_correo("nadie@x.co") is None
    assert usuarios.buscar_distribuidor_por_codigo("DIS-TEST01").id == distribuidor.id
    assert usuarios.buscar_distribuidor_por_codigo("DIS-NOEXIS") is None


def test_inactivar_es_baja_logica_y_oculta_al_distribuidor(usuarios, cliente, distribuidor):
    usuarios.inactivar(cliente.id)
    assert usuarios.buscar_por_id(cliente.id).activo is False
    usuarios.inactivar(distribuidor.id)
    assert usuarios.buscar_distribuidor_por_codigo("DIS-TEST01") is None
    with pytest.raises(NoEncontradoError):
        usuarios.inactivar(999999)


def test_busquedas_por_filtro_y_por_tipo(usuarios, cliente, distribuidor):
    assert {type(u).__name__ for u in usuarios.buscar_por_filtro("")} == {"Cliente", "Empleado", "Distribuidor"}
    assert [c.id for c in usuarios.buscar_clientes("laura")] == [cliente.id]
    assert usuarios.buscar_clientes("zzz") == []
    assert len(usuarios.buscar_empleados("")) == 3
    assert [e.documento for e in usuarios.buscar_empleados("E-1002")] == ["E-1002"]
    codigos = {d.codigo for d in usuarios.buscar_distribuidores("")}
    assert codigos == {"DIS-ANDES1", "DIS-TEST01"}
    assert [d.id for d in usuarios.buscar_distribuidores("DIS-TEST")] == [distribuidor.id]
    assert all(isinstance(u, Distribuidor) for u in usuarios.buscar_distribuidores("andes"))


def test_buscar_por_id_inexistente(usuarios):
    with pytest.raises(NoEncontradoError):
        usuarios.buscar_por_id(999999)


def test_correo_duplicado_lanza_duplicado_error(usuarios, cliente, nuevo_cliente):
    with pytest.raises(DuplicadoError) as e:
        usuarios.insertar(nuevo_cliente())
    assert e.value.campo == "correo"
