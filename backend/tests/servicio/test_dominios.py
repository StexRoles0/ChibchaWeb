"""CU-DOM-01 y CU-DOM-02: ServicioDominios con repositorio en memoria y registrador falso."""

import pytest

from chibchaweb.dominio.dominios_web import EstadoSolicitud
from chibchaweb.dominio.errores import (
    ContingenciaActivaError,
    EstadoInvalidoError,
    NoEncontradoError,
    UsuarioInactivoError,
    ValidacionError,
)
from chibchaweb.servicio.dto import ResumenDTO


# --- DOM-01 (RN-16) ------------------------------------------------------------------------------
def test_rn16_registrar_solicitud_queda_registrada_y_en_minusculas(dominios, solicitudes, cliente_registrado):
    id = dominios.registrar_solicitud_dominio(cliente_registrado.id, "TiendaLaura", ".CO")
    s = solicitudes.buscar_por_id(id)
    assert (s.nombre_completo(), s.estado, s.solicitante) == (
        "tiendalaura.co",
        EstadoSolicitud.REGISTRADA,
        cliente_registrado,
    )
    assert s.esta_pendiente() and s.fecha_envio is None


def test_rn16_la_extension_puede_venir_sin_punto(dominios, solicitudes, cliente_registrado):
    id = dominios.registrar_solicitud_dominio(cliente_registrado.id, "mitienda", "com")
    assert solicitudes.buscar_por_id(id).extension == ".com"


@pytest.mark.parametrize("nombre", ["", "-inicio", "fin-", "con espacio", "ñandú", "a" * 64, "punto.punto"])
def test_rn16_nombre_invalido_es_422_y_no_se_guarda(dominios, solicitudes, cliente_registrado, nombre):
    with pytest.raises(ValidacionError) as error:
        dominios.registrar_solicitud_dominio(cliente_registrado.id, nombre, ".com")
    assert error.value.campo == "nombre"
    assert solicitudes.buscar_por_filtro("") == []


def test_rn16_nombre_de_63_caracteres_es_valido(dominios, cliente_registrado):
    assert dominios.registrar_solicitud_dominio(cliente_registrado.id, "a" * 63, ".org")


@pytest.mark.parametrize("extension", [".xyz", "", ".", ".co.uk"])
def test_rn16_extension_no_admitida_es_422(dominios, solicitudes, cliente_registrado, extension):
    with pytest.raises(ValidacionError) as error:
        dominios.registrar_solicitud_dominio(cliente_registrado.id, "mitienda", extension)
    assert error.value.campo == "extension"
    assert solicitudes.buscar_por_filtro("") == []


def test_registrar_solicitud_cliente_inexistente_inactivo_o_no_cliente(dominios, cliente_registrado, empleado_gestion):
    with pytest.raises(NoEncontradoError):
        dominios.registrar_solicitud_dominio(999, "mitienda", ".co")
    with pytest.raises(NoEncontradoError):
        dominios.registrar_solicitud_dominio(empleado_gestion.id, "mitienda", ".co")
    cliente_registrado.inactivar()
    with pytest.raises(UsuarioInactivoError):
        dominios.registrar_solicitud_dominio(cliente_registrado.id, "mitienda", ".co")


def test_registrar_solicitud_con_contingencia_propaga_el_503(dominios, solicitudes, cliente_registrado):
    solicitudes.fallar_con = ContingenciaActivaError("BD caída; respaldado")
    with pytest.raises(ContingenciaActivaError):
        dominios.registrar_solicitud_dominio(cliente_registrado.id, "mitienda", ".co")


# --- DOM-02 (RN-17, RN-18) -----------------------------------------------------------------------
def test_rn17_enviar_solicitud_queda_enviada_con_fecha_de_envio(dominios, solicitudes, registrador, cliente_registrado):
    id = dominios.registrar_solicitud_dominio(cliente_registrado.id, "tiendalaura", ".co")
    assert dominios.generar_y_enviar_solicitud_xml(id) is EstadoSolicitud.ENVIADA
    s = solicitudes.buscar_por_id(id)
    assert s.estado is EstadoSolicitud.ENVIADA and s.fecha_envio is not None
    assert len(registrador.enviados) == 1


def test_rn18_el_xml_enviado_sigue_el_anexo_de_api_md(dominios, registrador, cliente_registrado):
    id = dominios.registrar_solicitud_dominio(cliente_registrado.id, "tiendalaura", ".co")
    dominios.generar_y_enviar_solicitud_xml(id)
    (xml,) = registrador.enviados
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<solicitudDominio>')
    assert "<solicitante><nombre>Laura Gómez</nombre><correo>laura@correo.co</correo></solicitante>" in xml
    assert "<dominio><nombre>tiendalaura</nombre><extension>.co</extension></dominio>" in xml
    assert xml.index("<solicitante>") < xml.index("<dominio>") < xml.index("<fecha>")
    assert xml.rstrip().endswith("</solicitudDominio>")


def test_rn17_registrador_caido_deja_la_solicitud_fallida(dominios, solicitudes, cliente_registrado):
    id = dominios.registrar_solicitud_dominio(cliente_registrado.id, "rechazo-total", ".com")
    assert dominios.generar_y_enviar_solicitud_xml(id) is EstadoSolicitud.FALLIDA
    s = solicitudes.buscar_por_id(id)
    assert s.estado is EstadoSolicitud.FALLIDA and s.fecha_envio is None


def test_el_cliente_puede_enviar_una_solicitud_nueva_tras_una_fallida(dominios, solicitudes, cliente_registrado):
    fallida = dominios.registrar_solicitud_dominio(cliente_registrado.id, "rechazo-total", ".com")
    dominios.generar_y_enviar_solicitud_xml(fallida)
    nueva = dominios.registrar_solicitud_dominio(cliente_registrado.id, "otra", ".com")
    assert dominios.generar_y_enviar_solicitud_xml(nueva) is EstadoSolicitud.ENVIADA


@pytest.mark.parametrize("nombre", ["tiendalaura", "rechazo-total"])
def test_rn17_solo_se_envia_una_solicitud_pendiente_409(dominios, registrador, cliente_registrado, nombre):
    id = dominios.registrar_solicitud_dominio(cliente_registrado.id, nombre, ".co")
    dominios.generar_y_enviar_solicitud_xml(id)
    enviados = len(registrador.enviados)
    with pytest.raises(EstadoInvalidoError):
        dominios.generar_y_enviar_solicitud_xml(id)
    assert len(registrador.enviados) == enviados


def test_enviar_solicitud_inexistente_es_404(dominios):
    with pytest.raises(NoEncontradoError):
        dominios.generar_y_enviar_solicitud_xml(999)


def test_enviar_con_contingencia_en_la_escritura_propaga_el_503(dominios, solicitudes, cliente_registrado):
    id = dominios.registrar_solicitud_dominio(cliente_registrado.id, "tiendalaura", ".co")
    solicitudes.fallar_con = ContingenciaActivaError("BD caída; respaldado")
    with pytest.raises(ContingenciaActivaError):
        dominios.generar_y_enviar_solicitud_xml(id)


# --- consultarSolicitudes ------------------------------------------------------------------------
def test_consultar_solicitudes_del_cliente_recientes_primero(dominios, cliente_registrado, cliente_suelto):
    a = dominios.registrar_solicitud_dominio(cliente_registrado.id, "primera", ".com")
    b = dominios.registrar_solicitud_dominio(cliente_registrado.id, "segunda", ".org")
    dominios.registrar_solicitud_dominio(cliente_suelto.id, "ajena", ".net")
    dominios.generar_y_enviar_solicitud_xml(a)
    filas = dominios.consultar_solicitudes(cliente_registrado.id)
    assert [(f.id, f.titulo, f.estado) for f in filas] == [
        (b, "segunda.org", "REGISTRADA"),
        (a, "primera.com", "ENVIADA"),
    ]
    assert len(filas[0].subtitulo) == 10 and filas[0].subtitulo[4] == "-"  # AAAA-MM-DD
    assert isinstance(filas[0], ResumenDTO)


def test_consultar_solicitudes_sin_solicitudes(dominios, cliente_registrado):
    assert dominios.consultar_solicitudes(cliente_registrado.id) == []
