"""RT04: si la BD falla, los 4 mapeadores respaldan el evento cifrado y `restaurar` lo reaplica (RN-29, RN-30)."""

import json
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from unittest import mock

import pytest
from django.db import InterfaceError, OperationalError
from django.db.models import Model
from django.db.models.query import QuerySet

from chibchaweb.dominio._comun import ZONA
from chibchaweb.dominio.cuentas import Distribuidor
from chibchaweb.dominio.dominios_web import EstadoSolicitud, SolicitudDominio
from chibchaweb.dominio.errores import ContingenciaActivaError, DuplicadoError, ReglaNegocioError
from chibchaweb.dominio.facturacion import Cheque, Comision, EstadoPago, Pago
from chibchaweb.dominio.soporte import CategoriaTicket, Ticket
from tests.falsos import PasarelaPagoFalsa

PERIODO = (date(2026, 12, 1), date(2026, 12, 31))


@contextmanager
def bd_caida(error=OperationalError):
    """Simula la caída de la BD: toda escritura del ORM falla con OperationalError."""
    with (
        mock.patch.object(Model, "save", side_effect=error("conexión perdida")),
        mock.patch.object(QuerySet, "update", side_effect=error("conexión perdida")),
    ):
        yield


def sincronizar(gestor, **repos):
    """Hace lo que hará ServicioContingencia: reparte cada evento al repositorio que le corresponde."""
    eventos = gestor.recuperar_pendientes()
    for evento in eventos:
        tipo, contenido = evento.split("|", 1)
        repos[tipo.split(".")[0]].restaurar(contenido)
    gestor.confirmar_sincronizacion()
    return [e.split("|", 1)[0] for e in eventos]


def lineas(ruta):
    return ruta.read_text(encoding="utf-8").splitlines()


# --- MapeadorUsuario -------------------------------------------------------------------------------


def test_usuario_insertar_respalda_y_restaura(usuarios, gestor, ruta_respaldo, nuevo_cliente):
    c = nuevo_cliente(correo="caida@correo.co")
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        usuarios.insertar(c)
    assert c.id is None and usuarios.buscar_por_correo("caida@correo.co") is None
    (linea,) = lineas(ruta_respaldo)
    algoritmo, tipo, cifrado = linea.split("|", 2)
    assert (algoritmo, tipo) == ("AES", "Usuario.insertar")
    assert "caida@correo.co" not in linea and "4242424242424242" not in linea  # cifrado
    contenido = gestor.recuperar_pendientes()[0]
    assert "caida@correo.co" in contenido and "4242424242424242" in contenido
    assert '"123"' not in contenido  # el código de seguridad (CVV) nunca se respalda
    assert "codigo_seguridad" not in contenido and "codigoSeguridad" not in contenido
    assert sincronizar(gestor, Usuario=usuarios) == ["Usuario.insertar"]
    assert lineas(ruta_respaldo) == []
    restaurado = usuarios.buscar_por_correo("caida@correo.co")
    assert restaurado.medio_pago.numero == "4242424242424242" and restaurado.residencia.ciudad == "Bogotá"
    assert restaurado.fecha_registro == c.fecha_registro


def test_usuario_actualizar_respalda_y_restaura(usuarios, gestor, cliente):
    cliente.nombre = "Laura Nueva"
    with bd_caida(InterfaceError), pytest.raises(ContingenciaActivaError):
        usuarios.actualizar(cliente)
    assert usuarios.buscar_por_id(cliente.id).nombre == "Laura Gómez"
    assert sincronizar(gestor, Usuario=usuarios) == ["Usuario.actualizar"]
    assert usuarios.buscar_por_id(cliente.id).nombre == "Laura Nueva"


def test_usuario_distribuidor_y_empleado_se_respaldan(usuarios, gestor, catalogo):
    d = Distribuidor("Caído SAS", "caido@x.co", "601", "9001", "DIS-CAIDO1")
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        usuarios.insertar(d)
    sincronizar(gestor, Usuario=usuarios)
    assert usuarios.buscar_distribuidor_por_codigo("DIS-CAIDO1").documento == "9001"


# --- MapeadorSuscripcion ---------------------------------------------------------------------------


def test_suscripcion_insertar_cobro_y_actualizar_se_respaldan_en_orden(
    suscripciones, gestor, ruta_respaldo, cliente, nueva_suscripcion
):
    s = nueva_suscripcion(cliente)
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        suscripciones.insertar(s)
    sincronizar(gestor, Suscripcion=suscripciones)
    (existente,) = suscripciones.buscar_por_filtro("tiendalaura")
    assert existente.sitio.subdominio == "tiendalaura.chibchaweb.com"

    # recargada desde la BD: cobrar y registrar durante la caída
    pago = existente.cobrar(PasarelaPagoFalsa())
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        suscripciones.registrar_pago(pago)
    with pytest.raises(RuntimeError, match="registrar_pago"):  # B5: no se descarta el pago nuevo en silencio
        suscripciones.actualizar(existente)
    assert sincronizar(gestor, Suscripcion=suscripciones) == ["Suscripcion.registrar_pago"]
    final = suscripciones.buscar_por_id(existente.id)
    assert len(final.pagos) == 1 and final.pagos[0].referencia_franquicia == pago.referencia_franquicia
    assert final.fecha_corte == existente.fecha_corte  # D-30: el corte avanzado viaja en el evento del pago
    final.suspender()
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        suscripciones.actualizar(final)
    assert sincronizar(gestor, Suscripcion=suscripciones) == ["Suscripcion.actualizar"]  # RN-30: orden escrito
    assert not suscripciones.buscar_por_id(existente.id).activa


# --- MapeadorComision ------------------------------------------------------------------------------


def test_comision_insertar_y_cheque_se_respaldan(
    comisiones, suscripciones, usuarios, gestor, nuevo_cliente, distribuidor, nueva_suscripcion
):
    referido = nuevo_cliente(correo="ref@correo.co")
    referido.asociar_distribuidor(distribuidor)
    usuarios.insertar(referido)
    s = nueva_suscripcion(referido, "ref")
    s.agregar_pago(
        Pago(
            Decimal("50.00"), EstadoPago.EXITOSO, s, fecha=datetime(2026, 12, 5, tzinfo=ZONA), referencia_franquicia="X"
        )
    )
    suscripciones.insertar(s)
    c = Comision(*PERIODO, 1, "Básico", Decimal("0.10"), distribuidor)
    for pago in suscripciones.buscar_pagos_para_comision(distribuidor, *PERIODO):
        c.agregar_pago_base(pago)
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        comisiones.insertar(c)
    assert c.id is None
    sincronizar(gestor, Comision=comisiones)
    (guardada,) = comisiones.buscar_por_filtro("Básico")
    assert guardada.calcular_monto() == Decimal("5.00") and len(guardada.pagos_base) == 1

    guardada.asociar_cheque(Cheque("CHQ-2026-000077", "Andes", Decimal("5.00"), date(2027, 1, 1)))
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        comisiones.registrar_cheque(guardada)
    assert comisiones.buscar_por_id(guardada.id).cheque is None
    assert sincronizar(gestor, Comision=comisiones) == ["Comision.registrar_cheque"]
    assert comisiones.buscar_por_id(guardada.id).cheque.numero == "CHQ-2026-000077"


# --- MapeadorSolicitudDominio ----------------------------------------------------------------------


def test_solicitud_insertar_y_actualizar_se_respaldan(solicitudes, gestor, cliente):
    s = SolicitudDominio("caida", ".co", cliente)
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        solicitudes.insertar(s)
    sincronizar(gestor, SolicitudDominio=solicitudes)
    (guardada,) = solicitudes.buscar_por_solicitante(cliente.id)
    guardada._marcar_fallida()
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        solicitudes.actualizar(guardada)
    sincronizar(gestor, SolicitudDominio=solicitudes)
    assert solicitudes.buscar_por_id(guardada.id).estado is EstadoSolicitud.FALLIDA


# --- comportamiento común ---------------------------------------------------------------------------


def test_el_algoritmo_activo_se_usa_y_cada_linea_se_lee_con_el_suyo(usuarios, gestor, ruta_respaldo, nuevo_cliente):
    for n, algoritmo in enumerate(("AES", "ChaCha20", "Camellia", "Twofish")):
        gestor.cambiar_algoritmo(algoritmo)
        with bd_caida(), pytest.raises(ContingenciaActivaError):
            usuarios.insertar(nuevo_cliente(correo=f"c{n}@correo.co"))
    assert [linea.split("|")[0] for linea in lineas(ruta_respaldo)] == ["AES", "ChaCha20", "Camellia", "Twofish"]
    sincronizar(gestor, Usuario=usuarios)
    assert all(usuarios.buscar_por_correo(f"c{n}@correo.co") for n in range(4))


def test_error_de_integridad_no_es_contingencia(usuarios, cliente, nuevo_cliente, ruta_respaldo):
    from chibchaweb.dominio.errores import DuplicadoError

    with pytest.raises(DuplicadoError):
        usuarios.insertar(nuevo_cliente())
    assert not ruta_respaldo.exists()


def test_si_el_respaldo_no_esta_disponible_se_avisa(usuarios, gestor, nuevo_cliente, tmp_path):
    from chibchaweb.dominio.respaldo import ArchivoPlano

    ocupado = tmp_path / "archivo"
    ocupado.write_text("x")
    gestor.cambiar_medio(ArchivoPlano(str(ocupado / "dentro" / "respaldo.log")))  # el padre es un archivo
    with bd_caida(), pytest.raises(ReglaNegocioError):
        usuarios.insertar(nuevo_cliente(correo="x@correo.co"))


def test_ticket_y_migracion_no_respaldan(tickets, migraciones, cliente, catalogo, ruta_respaldo, usuarios):
    from chibchaweb.dominio.migracion import ProcesoMigracion

    t = Ticket("x", CategoriaTicket.OTRA, cliente, catalogo.buscar_nivel_inicial())
    with bd_caida(), pytest.raises(OperationalError):
        tickets.insertar(t)
    p = ProcesoMigracion(usuarios.buscar_empleados("admin@")[0], list(migraciones._creadores))
    with bd_caida(), pytest.raises(OperationalError):
        migraciones.insertar(p)
    assert not ruta_respaldo.exists()


# --- B4: lecturas y registro con la BD caída ---------------------------------------------------------


def test_registro_respaldado_incluye_la_suscripcion_y_restaurar_recrea_ambos(
    usuarios, suscripciones, gestor, ruta_respaldo, nuevo_cliente, nueva_suscripcion
):
    c = nuevo_cliente(correo="nuevo@correo.co")
    nueva_suscripcion(c, "sitionuevo")
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        usuarios.insertar(c)
    assert "sitionuevo" in gestor.recuperar_pendientes()[0] and "sitionuevo" not in lineas(ruta_respaldo)[0]
    assert sincronizar(gestor, Usuario=usuarios) == ["Usuario.insertar"]
    restaurado = usuarios.buscar_por_correo("nuevo@correo.co")
    (s,) = restaurado.suscripciones
    assert s.sitio.subdominio == "sitionuevo.chibchaweb.com" and s.activa and s.paquete.id == 2 and s.plan.id == 3
    assert [x.sitio.subdominio for x in suscripciones.buscar_por_filtro("sitionuevo")] == ["sitionuevo.chibchaweb.com"]


def test_insertar_normal_no_escribe_la_suscripcion_la_escribe_su_mapeador(
    usuarios, suscripciones, nuevo_cliente, nueva_suscripcion
):
    c = nuevo_cliente(correo="normal@correo.co")
    s = nueva_suscripcion(c, "sitionormal")
    usuarios.insertar(c)
    assert suscripciones.buscar_por_filtro("sitionormal") == []
    suscripciones.insertar(s)
    assert len(suscripciones.buscar_por_filtro("sitionormal")) == 1


def test_una_lectura_con_la_bd_caida_es_contingencia_y_no_respalda(
    usuarios, suscripciones, comisiones, solicitudes, tickets, migraciones, catalogo, ruta_respaldo
):
    lecturas = [
        lambda: usuarios.buscar_por_id(1),
        lambda: usuarios.buscar_por_correo("a@b.co"),
        lambda: usuarios.buscar_clientes(""),
        lambda: suscripciones.buscar_vencidas(date(2026, 1, 1)),
        lambda: comisiones.buscar_por_filtro(""),
        lambda: solicitudes.buscar_por_solicitante(1),
        lambda: tickets.buscar_abiertos(),
        lambda: migraciones.buscar_por_filtro(""),
        lambda: catalogo.listar_paquetes(),
        lambda: catalogo.buscar_nivel_inicial(),
        lambda: usuarios.existe(1),
    ]
    for lectura in lecturas:
        for error in (OperationalError, InterfaceError):
            with (
                mock.patch.object(QuerySet, "_fetch_all", side_effect=error("sin conexión")),
                mock.patch("chibchaweb.persistencia.mapeadores.base.connection.cursor", side_effect=error("caída")),
                pytest.raises(ContingenciaActivaError),
            ):
                lectura()
    assert not ruta_respaldo.exists() or lineas(ruta_respaldo) == []


def test_nombre_tabla_gestor_y_creadores_son_propiedades(usuarios, suscripciones, comisiones, solicitudes, tickets):
    assert usuarios.nombre_tabla == "usuario" and suscripciones.nombre_tabla == "suscripcion"
    for mapeador in (usuarios, suscripciones, comisiones, solicitudes, tickets):
        assert mapeador.gestor is mapeador._gestor  # noqa: SLF001


# --- D-33: un evento respaldado debe ser autosuficiente ---------------------------------------------


def _distribuidor(n):
    return Distribuidor(f"Dist {n}", f"caida{n}@x.co", "601", f"80{n}", f"DIS-CAI{n:03d}")


def test_d32_caida_tras_una_escritura_previa_de_la_transaccion_no_respalda(usuarios, gestor, ruta_respaldo):
    from chibchaweb.persistencia.transacciones import UnidadDeTrabajoDjango

    unidad = UnidadDeTrabajoDjango()
    unidad.iniciar()
    usuarios.insertar(_distribuidor(1))  # escritura previa dentro de la misma transacción
    with bd_caida(), pytest.raises(ContingenciaActivaError, match="no quedó respaldada"):
        usuarios.insertar(_distribuidor(2))
    unidad.revertir()
    assert not ruta_respaldo.exists() or lineas(ruta_respaldo) == []  # ningún evento huérfano
    assert gestor.recuperar_pendientes() == []
    assert usuarios.buscar_por_correo("caida1@x.co") is None  # el rollback dejó la BD coherente


def test_d32_caida_en_la_primera_escritura_de_la_transaccion_respalda_y_se_sincroniza(usuarios, gestor, ruta_respaldo):
    from chibchaweb.persistencia.transacciones import UnidadDeTrabajoDjango

    unidad = UnidadDeTrabajoDjango()
    unidad.iniciar()
    with bd_caida(), pytest.raises(ContingenciaActivaError, match="quedó respaldada"):
        usuarios.insertar(_distribuidor(3))
    unidad.revertir()
    assert len(lineas(ruta_respaldo)) == 1
    assert sincronizar(gestor, Usuario=usuarios) == ["Usuario.insertar"]
    assert usuarios.buscar_por_correo("caida3@x.co") is not None


def test_d32_la_cuenta_se_reinicia_al_cerrar_la_transaccion(usuarios, gestor, ruta_respaldo):
    from chibchaweb.persistencia.transacciones import UnidadDeTrabajoDjango

    unidad = UnidadDeTrabajoDjango()
    unidad.iniciar()
    usuarios.insertar(_distribuidor(4))
    unidad.confirmar()
    unidad.iniciar()  # transacción nueva: sin escrituras previas
    with bd_caida(), pytest.raises(ContingenciaActivaError, match="quedó respaldada"):
        usuarios.insertar(_distribuidor(5))
    unidad.revertir()
    assert len(lineas(ruta_respaldo)) == 1


# --- eventos malformados: ReglaNegocioError (no KeyError/IntegrityError) -----------------------------


def _evento_de_solicitud(solicitudes, gestor, cliente):
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        solicitudes.insertar(SolicitudDominio("rota", "co", cliente))
    return json.loads(gestor.recuperar_pendientes()[0].split("|", 1)[1])


def test_restaurar_usuario_actualizar_sin_campos_es_regla_de_negocio(usuarios):
    with pytest.raises(ReglaNegocioError, match="inválido"):
        usuarios.restaurar('{"_operacion":"actualizar","id":9999}')


@pytest.mark.parametrize("repo", ["usuarios", "suscripciones", "comisiones", "solicitudes"])
@pytest.mark.parametrize("contenido", ["no es json", "{}", '{"_operacion":"insertar"}', "[]", "null"])
def test_restaurar_contenido_malformado_es_regla_de_negocio(request, repo, contenido):
    with pytest.raises(ReglaNegocioError):
        request.getfixturevalue(repo).restaurar(contenido)


def test_restaurar_solicitud_que_rompe_un_check_es_regla_de_negocio_y_no_deja_filas(solicitudes, gestor, cliente):
    datos = _evento_de_solicitud(solicitudes, gestor, cliente)
    datos |= {"estado": "ENVIADA", "fecha_envio": None}
    with pytest.raises(ReglaNegocioError, match="restricción"):
        solicitudes.restaurar(json.dumps(datos))
    assert solicitudes.buscar_por_solicitante(cliente.id) == []


def test_restaurar_no_toca_un_duplicado_unique(usuarios, cliente, nuevo_cliente, gestor):
    otro = nuevo_cliente(correo="dup@correo.co")
    with bd_caida(), pytest.raises(ContingenciaActivaError):
        usuarios.insertar(otro)
    datos = json.loads(gestor.recuperar_pendientes()[0].split("|", 1)[1]) | {"correo": cliente.correo}
    with pytest.raises(DuplicadoError):
        usuarios.restaurar(json.dumps(datos))
