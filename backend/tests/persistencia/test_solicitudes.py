"""MapeadorSolicitudDominio."""

import pytest

from chibchaweb.dominio.dominios_web import EstadoSolicitud, SolicitudDominio
from chibchaweb.dominio.errores import NoEncontradoError
from tests.falsos import RegistradorDominioFalso


def test_ida_y_vuelta_y_cambio_de_estado(solicitudes, cliente):
    s = SolicitudDominio("TiendaLaura", "co", cliente)
    id = solicitudes.insertar(s)
    assert s.id == id
    leida = solicitudes.buscar_por_id(id)
    assert leida is not s and leida.solicitante.id == cliente.id and leida.solicitante.correo == cliente.correo
    assert (leida.nombre, leida.extension, leida.estado) == ("tiendalaura", ".co", EstadoSolicitud.REGISTRADA)
    assert leida.fecha_solicitud == s.fecha_solicitud and leida.fecha_envio is None and leida.esta_pendiente()
    s.enviar_a(
        RegistradorDominioFalso(),
        s.construir_documento(__import__("chibchaweb.dominio.dominios_web", fromlist=["x"]).ConstructorXML()),
    )
    solicitudes.actualizar(s)
    enviada = solicitudes.buscar_por_id(id)
    assert enviada.estado is EstadoSolicitud.ENVIADA and enviada.fecha_envio == s.fecha_envio


def test_consultas(solicitudes, cliente, nuevo_cliente, usuarios):
    otro = nuevo_cliente(correo="otro@correo.co", nombre="Pedro Pérez")
    usuarios.insertar(otro)
    a, b = SolicitudDominio("uno", ".com", cliente), SolicitudDominio("dos", ".net", otro)
    solicitudes.insertar(a)
    solicitudes.insertar(b)
    assert [s.id for s in solicitudes.buscar_por_solicitante(cliente.id)] == [a.id]
    assert [s.id for s in solicitudes.buscar_por_solicitante(otro.id)] == [b.id]
    assert solicitudes.buscar_por_solicitante(999999) == []
    assert [s.id for s in solicitudes.buscar_por_filtro("pedro")] == [b.id]
    assert [s.id for s in solicitudes.buscar_por_filtro(".com")] == [a.id]
    assert len(solicitudes.buscar_por_filtro("")) == 2
    with pytest.raises(NoEncontradoError):
        solicitudes.buscar_por_id(999999)
