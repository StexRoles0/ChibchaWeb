"""Solicitud de dominio y Builder del XML: RN-16, RN-17 y RN-18."""

import xml.etree.ElementTree as ET
from datetime import date, datetime

import pytest
from freezegun import freeze_time

from chibchaweb.dominio._comun import ZONA
from chibchaweb.dominio.dominios_web import ConstructorSolicitud, ConstructorXML, EstadoSolicitud, SolicitudDominio
from chibchaweb.dominio.errores import EstadoInvalidoError, ValidacionError
from tests.falsos import RegistradorDominioFalso

FECHA = datetime(2026, 11, 16, 10, 30, tzinfo=ZONA)


def _solicitud(cliente, nombre="tiendalaura", extension=".co"):
    return SolicitudDominio(nombre, extension, cliente, fecha_solicitud=FECHA)


# --- RN-16 formato ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nombre", "extension"),
    [("tiendalaura", ".co"), ("a", ".com"), ("mi-tienda-2", ".net"), ("x" * 63, ".org"), ("TiendaLaura", "co")],
)
def test_rn16_formatos_validos(cliente, nombre, extension):
    assert _solicitud(cliente, nombre, extension).validar_formato() is True


@pytest.mark.parametrize(
    ("nombre", "extension"),
    [
        ("", ".co"),
        ("-tienda", ".co"),
        ("tienda-", ".co"),
        ("x" * 64, ".co"),
        ("mi tienda", ".co"),
        ("tienda_laura", ".co"),
        ("tiendá", ".co"),
        ("tienda", ".io"),
        ("tienda", ""),
    ],
)
def test_rn16_formatos_invalidos_lanzan_validacion_con_el_campo_que_fallo(cliente, nombre, extension):
    with pytest.raises(ValidacionError) as error:
        _solicitud(cliente, nombre, extension).validar_formato()
    assert error.value.campo == ("extension" if nombre in ("tienda",) else "nombre")


def test_rn16_si_fallan_los_dos_campos_se_informa_el_nombre(cliente):
    with pytest.raises(ValidacionError) as error:
        _solicitud(cliente, "-x", ".io").validar_formato()
    assert error.value.campo == "nombre"


def test_rn16_nombre_se_guarda_en_minusculas(cliente):
    s = _solicitud(cliente, " TiendaLaura ", "CO")
    assert s.nombre == "tiendalaura" and s.extension == ".co" and s.nombre_completo() == "tiendalaura.co"


# --- RN-17 estados ----------------------------------------------------------------------------


@freeze_time("2026-11-16 16:00:00")
def test_rn17_envio_exitoso_queda_enviada_con_fecha(cliente):
    s = _solicitud(cliente)
    assert s.esta_pendiente() and s.estado is EstadoSolicitud.REGISTRADA and s.fecha_envio is None
    registrador = RegistradorDominioFalso()
    s.enviar_a(registrador, "<xml/>")
    assert s.estado is EstadoSolicitud.ENVIADA and not s.esta_pendiente()
    assert s.fecha_envio == datetime(2026, 11, 16, 11, 0, tzinfo=ZONA)
    assert registrador.enviados == ["<xml/>"]


def test_rn17_falla_de_red_queda_fallida(cliente):
    s = _solicitud(cliente, "rechazo")
    s.enviar_a(RegistradorDominioFalso(), s.construir_documento(ConstructorXML()))
    assert s.estado is EstadoSolicitud.FALLIDA and s.fecha_envio is None


@pytest.mark.parametrize("estado", [EstadoSolicitud.ENVIADA, EstadoSolicitud.FALLIDA])
def test_rn17_solo_se_envia_una_pendiente(cliente, estado):
    s = SolicitudDominio("tienda", ".co", cliente, id=1, estado=estado)
    with pytest.raises(EstadoInvalidoError):
        s.enviar_a(RegistradorDominioFalso(), "<xml/>")


def test_rn17_documento_vacio_falla(cliente):
    with pytest.raises(ValidacionError):
        _solicitud(cliente).enviar_a(RegistradorDominioFalso(), "  ")


def test_solicitud_validaciones(cliente):
    with pytest.raises(ValidacionError):
        SolicitudDominio("a", ".co", None)  # type: ignore[arg-type]
    with pytest.raises(ValidacionError):
        SolicitudDominio("a", ".co", cliente, estado="ENVIADA")  # type: ignore[arg-type]
    s = _solicitud(cliente)
    assert s.solicitante is cliente and s.fecha_solicitud == FECHA and "tiendalaura.co" in repr(s)
    assert [e.value for e in EstadoSolicitud] == ["REGISTRADA", "ENVIADA", "FALLIDA"]


# --- RN-18 Builder -----------------------------------------------------------------------------


def test_rn18_director_produce_el_xml_del_anexo(cliente):
    xml = _solicitud(cliente).construir_documento(ConstructorXML())
    assert xml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<solicitudDominio>\n"
        "  <solicitante><nombre>Laura Gómez</nombre><correo>laura@correo.co</correo></solicitante>\n"
        "  <dominio><nombre>tiendalaura</nombre><extension>.co</extension></dominio>\n"
        "  <fecha>2026-11-16T10:30:00-05:00</fecha>\n"
        "</solicitudDominio>\n"
    )
    raiz = ET.fromstring(xml.encode("utf-8"))
    assert raiz.find("dominio/nombre").text == "tiendalaura"


def test_rn18_director_llama_los_pasos_en_orden(cliente):
    class ConstructorEspia(ConstructorSolicitud):
        def __init__(self):
            self.pasos = []

        def iniciar_documento(self):
            self.pasos.append("iniciar")

        def agregar_solicitante(self, c):
            self.pasos.append(("solicitante", c))

        def agregar_dominio(self, nombre, extension):
            self.pasos.append(("dominio", nombre, extension))

        def agregar_fecha(self, fecha):
            self.pasos.append(("fecha", fecha))

        def obtener_resultado(self):
            self.pasos.append("resultado")
            return "DOC"

    espia = ConstructorEspia()
    assert _solicitud(cliente).construir_documento(espia) == "DOC"
    assert espia.pasos == [
        "iniciar",
        ("solicitante", cliente),
        ("dominio", "tiendalaura", ".co"),
        ("fecha", FECHA),
        "resultado",
    ]


def test_rn18_no_construye_si_el_formato_es_invalido(cliente):
    with pytest.raises(ValidacionError):
        _solicitud(cliente, "-mal").construir_documento(ConstructorXML())


def test_rn18_constructor_xml_escapa_y_controla_su_ciclo(nuevo_cliente):
    c = ConstructorXML()
    assert c.contenido == ""
    with pytest.raises(EstadoInvalidoError):
        c.agregar_dominio("a", ".co")
    with pytest.raises(EstadoInvalidoError):
        c.obtener_resultado()
    c.iniciar_documento()
    c.agregar_solicitante(nuevo_cliente(nombre="Ana & <Co>"))
    c.agregar_fecha(date(2026, 11, 16))
    c.agregar_fecha(datetime(2026, 11, 16, 8, 0))  # sin zona: se asume Bogotá
    resultado = c.obtener_resultado()
    assert "Ana &amp; &lt;Co&gt;" in resultado and "<fecha>2026-11-16</fecha>" in resultado
    assert "2026-11-16T08:00:00-05:00" in resultado
    assert c.obtener_resultado() == resultado  # cerrar dos veces no duplica
    with pytest.raises(EstadoInvalidoError):
        c.agregar_dominio("a", ".co")
    with pytest.raises(TypeError):
        ConstructorSolicitud()  # type: ignore[abstract]
