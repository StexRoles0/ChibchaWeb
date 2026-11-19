"""RT04 con la BD caída DE VERDAD (D-30): se cortan los sockets de PostgreSQL, no se simula con mocks de ORM.

Qué se garantiza y qué no (limitación documentada): con la BD completamente caída, toda petición responde 503
``CONTINGENCIA`` (nunca 500) y la sesión sigue valiendo porque vive en la cookie. Como todo caso de uso LEE la BD
antes de escribir (usuario, catálogo, suscripciones…), esas lecturas fallan con 503 sin respaldar nada; el evento
solo se respalda cuando la conexión se pierde después de las lecturas, en la propia escritura del agregado.
"""

from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from chibchaweb.adaptadores.simulados import ValidadorMedioPagoSimulado
from config.contenedor import contenedor
from tests.web.conftest import BASE, assert_error, empleado_en_sesion
from tests.web.conftest import cliente_en_sesion as _registrar

ME = f"{BASE}/clientes/me"
PENDIENTES = f"{BASE}/contingencia/pendientes"
SINCRONIZACION = f"{BASE}/contingencia/sincronizacion"

PAGO = {
    "lineaFacturacion": "Avenida 68 # 10-10",
    "ciudadFacturacion": "Medellín",
    "codigoPostalFacturacion": "050001",
    "numeroTarjeta": "5105105105105100",
    "vencimiento": "2099-01-01",
    "codigoSeguridad": "123",
    "franquicia": "MASTERCARD",
}


def cliente_en_sesion(correo: str):
    """La BD aislada se comparte entre las pruebas del módulo: cada una usa su propio correo y sitio."""
    return _registrar(correo, sitio=correo.split("@")[0])


def tarjeta_de(http) -> str:
    return dict(c.split(": ", 1) for c in http.get(ME).json()["campos"])["tarjeta"]


def test_con_la_bd_cortada_toda_peticion_es_503_contingencia_y_nunca_500(bd):
    cliente = cliente_en_sesion("lectura@correo.co")
    admin = empleado_en_sesion("admin@chibchaweb.co")
    bd.cortar()

    # lecturas
    assert_error(cliente.get(f"{BASE}/catalogo/paquetes"), 503, "CONTINGENCIA")
    assert_error(cliente.get(ME), 503, "CONTINGENCIA")
    # escrituras: abrir la transacción de la petición ya falla (antes se veía un 500)
    assert_error(cliente.patch(f"{ME}?categoria=PERSONAL", {"nombre": "X"}, format="json"), 503, "CONTINGENCIA")
    assert_error(cliente.delete(ME), 503, "CONTINGENCIA")
    assert_error(admin.post(f"{BASE}/migraciones", {}, format="json"), 503, "CONTINGENCIA")
    # el inicio de sesión también responde 503 (la identidad se busca en la BD)
    from rest_framework.test import APIClient

    visitante = APIClient()
    inicio = visitante.get(f"{BASE}/auth/oauth/inicio", {"correo": "otro@correo.co"})
    assert inicio.status_code == 200  # no necesita la BD
    estado = inicio.json()["url"].split("state=")[1]
    assert_error(
        visitante.post(
            f"{BASE}/auth/oauth/callback", {"codigo": "dev:otro@correo.co", "estado": estado}, format="json"
        ),
        503,
        "CONTINGENCIA",
    )

    # la sesión no depende de la BD: el administrador sigue autenticado y ve el respaldo (no hace falta la BD)
    assert admin.get(f"{BASE}/auth/sesion").status_code == 200
    assert admin.get(PENDIENTES).json() == []  # las lecturas fallidas no respaldaron nada (limitación documentada)

    bd.restablecer()
    assert cliente.get(ME).status_code == 200  # al volver la BD, la misma sesión sigue valiendo
    assert admin.get(f"{BASE}/catalogo/paquetes").status_code == 200


def test_la_conexion_se_corta_en_plena_peticion_se_respalda_y_se_sincroniza_al_volver(bd):
    cliente = cliente_en_sesion("mitad@correo.co")
    admin = empleado_en_sesion("admin@chibchaweb.co")
    antes = tarjeta_de(cliente)
    assert antes == "VISA •••• 4242"

    # La BD cae justo después de las lecturas del caso de uso, cuando el servicio ya va a escribir.
    original = ValidadorMedioPagoSimulado.verificar

    def verificar_y_caer(self, medio):
        bd.cortar()
        return original(self, medio)

    with mock.patch.object(ValidadorMedioPagoSimulado, "verificar", verificar_y_caer):
        respuesta = cliente.patch(f"{ME}?categoria=PAGO", PAGO, format="json")
    assert_error(respuesta, 503, "CONTINGENCIA")
    assert "respaldada" in respuesta.json()["mensaje"]  # esta sí llegó a un mapeador: el evento quedó respaldado

    # el evento está en el archivo plano, cifrado, sin el número de tarjeta ni el código de seguridad en claro
    texto = open(contenedor().gestor.medio.ruta, encoding="utf-8").read()
    assert texto.startswith("AES|Usuario.actualizar|") and "5105105105105100" not in texto
    pendientes = admin.get(PENDIENTES)  # con la BD todavía caída: el listado no la necesita ni descifra nada
    assert pendientes.json() == [{"id": 1, "titulo": "Usuario.actualizar", "subtitulo": "AES", "estado": "PENDIENTE"}]
    # la sincronización con la BD aún caída es 503 y el respaldo queda intacto (RN-30)
    assert_error(admin.post(SINCRONIZACION, {}, format="json"), 503, "CONTINGENCIA")
    assert len(admin.get(PENDIENTES).json()) == 1

    bd.restablecer()
    assert tarjeta_de(cliente) == antes  # la escritura nunca llegó a la BD
    sincronizada = admin.post(SINCRONIZACION, {}, format="json")
    assert sincronizada.status_code == 200 and sincronizada.json() == {"sincronizados": 1}
    assert admin.get(PENDIENTES).json() == []
    assert tarjeta_de(cliente) == "MASTERCARD •••• 5100"  # el evento respaldado se reaplicó


def test_las_tareas_con_la_bd_cortada_terminan_con_error_sin_cobrar(bd):
    cliente = cliente_en_sesion("tareas@correo.co")
    bd.cortar()
    with pytest.raises(CommandError, match="Contingencia activa"):
        call_command("cargar_pagos", "--fecha", "2099-01-01", stdout=StringIO())
    assert contenedor().gestor.recuperar_pendientes() == []
    bd.restablecer()
    salida = StringIO()
    call_command("cargar_pagos", "--fecha", "2099-01-01", stdout=salida)
    assert "cobros procesados" in salida.getvalue() and "0 cobros" not in salida.getvalue()
    (suscripcion,) = contenedor().usuarios.buscar_por_id(cliente.id_usuario).suscripciones
    assert len(suscripcion.pagos) == 1  # al volver la BD se cobró una sola vez
