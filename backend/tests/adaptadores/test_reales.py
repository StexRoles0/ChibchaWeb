"""Adaptadores reales con transporte HTTP simulado (httpx.MockTransport): no llaman a servicios externos."""

import json
import time
from datetime import date
from decimal import Decimal

import httpx
import pytest
from joserfc import jwt
from joserfc.jwk import KeySet, RSAKey

from chibchaweb.adaptadores.legado import AdaptadorSistemaLegado
from chibchaweb.adaptadores.oauth import AdaptadorOAuth
from chibchaweb.adaptadores.pagos import AdaptadorProcesadorPagos, AdaptadorValidadorTarjeta
from chibchaweb.adaptadores.registrador import AdaptadorRegistradorDominio
from chibchaweb.dominio.cuentas import TarjetaCredito
from chibchaweb.dominio.errores import AutorizacionFallidaError, ReglaNegocioError, ValidacionError
from chibchaweb.dominio.integraciones import FuenteLegada, PasarelaPago, ProveedorAutenticacion
from tests import falsos


def cliente_http(manejador):
    return httpx.Client(transport=httpx.MockTransport(manejador))


def tarjeta(codigo="123", numero="4242424242424242"):
    return TarjetaCredito(numero, date(2030, 12, 1), falsos.franquicias_estandar()[0], codigo)


# --- OAuth ---------------------------------------------------------------------------------------------

PROVEEDOR = "https://proveedor.test"
APP = "app-chibcha"


class ProveedorOidcFalso:
    """Servidor OIDC mínimo: descubrimiento, endpoint de token y JWKS."""

    def __init__(self, **claims):
        self.llave = RSAKey.generate_key(2048, parameters={"kid": "k1", "use": "sig"})
        self.claims = {
            "iss": PROVEEDOR,
            "aud": APP,
            "sub": "1234567890",
            "exp": int(time.time()) + 300,
            "email": "laura@correo.co",
            "email_verified": True,
            "name": "Laura Gómez",
        } | claims
        self.token_status = 200
        self.firmante = self.llave
        self.peticiones: list[httpx.Request] = []

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        self.peticiones.append(peticion)
        ruta = peticion.url.path
        if ruta == "/.well-known/openid-configuration":
            return httpx.Response(
                200, json={"issuer": PROVEEDOR, "token_endpoint": f"{PROVEEDOR}/token", "jwks_uri": f"{PROVEEDOR}/jwks"}
            )
        if ruta == "/token":
            if self.token_status != 200:
                return httpx.Response(self.token_status, json={"error": "invalid_grant"})
            id_token = jwt.encode({"alg": "RS256", "kid": "k1"}, self.claims, self.firmante)
            return httpx.Response(200, json={"access_token": "a", "token_type": "Bearer", "id_token": id_token})
        if ruta == "/jwks":
            return httpx.Response(200, json=KeySet([self.llave]).as_dict(private=False))
        return httpx.Response(404)

    def adaptador(self) -> AdaptadorOAuth:
        return AdaptadorOAuth(
            PROVEEDOR, APP, "secreto", "http://localhost:4200/auth/callback", httpx.MockTransport(self)
        )


def test_oauth_intercambia_el_codigo_y_valida_el_id_token():
    servidor = ProveedorOidcFalso()
    adaptador = servidor.adaptador()
    assert isinstance(adaptador, ProveedorAutenticacion)
    assert (adaptador.url_proveedor, adaptador.id_aplicacion) == (PROVEEDOR, APP)
    identidad = adaptador.autorizar("codigo-de-un-solo-uso")
    assert identidad.identificador_externo == "1234567890" and identidad.correo == "laura@correo.co"
    assert identidad.nombre == "Laura Gómez" and identidad.correo_verificado
    token = next(p for p in servidor.peticiones if p.url.path == "/token")
    cuerpo = dict(x.split("=") for x in token.content.decode().split("&"))
    assert cuerpo["code"] == "codigo-de-un-solo-uso" and cuerpo["grant_type"] == "authorization_code"
    assert cuerpo["client_id"] == APP and "client_secret" in cuerpo


def test_oauth_correo_no_verificado():
    assert not ProveedorOidcFalso(email_verified=False).adaptador().autorizar("c").correo_verificado
    assert not ProveedorOidcFalso(email_verified="true").adaptador().autorizar("c").correo_verificado


@pytest.mark.parametrize(
    "claims",
    [{"aud": "otra-app"}, {"iss": "https://falso.test"}, {"exp": int(time.time()) - 10}, {"sub": None}],
)
def test_oauth_rechaza_tokens_invalidos(claims):
    servidor = ProveedorOidcFalso(**claims)
    if claims.get("sub", 1) is None:
        del servidor.claims["sub"]
    with pytest.raises(AutorizacionFallidaError):
        servidor.adaptador().autorizar("c")


def test_oauth_rechaza_firma_de_otra_llave_y_codigo_rechazado():
    servidor = ProveedorOidcFalso()
    servidor.firmante = RSAKey.generate_key(2048, parameters={"kid": "k1", "use": "sig"})
    with pytest.raises(AutorizacionFallidaError):
        servidor.adaptador().autorizar("c")
    rechazado = ProveedorOidcFalso()
    rechazado.token_status = 400
    with pytest.raises(AutorizacionFallidaError):
        rechazado.adaptador().autorizar("c")
    with pytest.raises(AutorizacionFallidaError):
        ProveedorOidcFalso().adaptador().autorizar("  ")


def test_oauth_exige_https_y_aplicacion():
    with pytest.raises(ValidacionError):
        AdaptadorOAuth("http://inseguro.test", APP)
    with pytest.raises(ValidacionError):
        AdaptadorOAuth(PROVEEDOR, " ")


# --- Validador de tarjetas -----------------------------------------------------------------------------


def test_validador_traduce_la_tarjeta_y_devuelve_el_veredicto():
    recibidas = []

    def manejador(peticion):
        recibidas.append(json.loads(peticion.content))
        return httpx.Response(200, json={"valida": recibidas[-1]["numero"] != "4000000000000002"})

    adaptador = AdaptadorValidadorTarjeta("https://verifica.test/tarjetas", cliente_http(manejador))
    assert adaptador.verificar(tarjeta()) is True
    assert recibidas[0] == {
        "numero": "4242424242424242",
        "vencimiento": "2030-12",
        "franquicia": "VISA",
        "codigoSeguridad": "123",
    }
    assert adaptador.verificar(tarjeta(codigo=None, numero="4000000000000002")) is False
    assert "codigoSeguridad" not in recibidas[1]


def test_validador_rechazo_http_error_y_red():
    assert (
        AdaptadorValidadorTarjeta("https://v.test", cliente_http(lambda p: httpx.Response(422))).verificar(tarjeta())
        is False
    )
    with pytest.raises(ReglaNegocioError):
        AdaptadorValidadorTarjeta("https://v.test", cliente_http(lambda p: httpx.Response(500))).verificar(tarjeta())

    def sin_red(peticion):
        raise httpx.ConnectError("sin red", request=peticion)

    with pytest.raises(ReglaNegocioError) as e:
        AdaptadorValidadorTarjeta("https://v.test", cliente_http(sin_red)).verificar(tarjeta())
    assert "4242" not in str(e.value) and e.value.__cause__ is None


# --- Procesador de pagos -------------------------------------------------------------------------------


def test_procesador_cobra_y_devuelve_la_referencia():
    recibidas = []

    def manejador(peticion):
        recibidas.append(json.loads(peticion.content))
        return httpx.Response(200, json={"aprobado": True, "referencia": "PROC-77"})

    adaptador = AdaptadorProcesadorPagos("https://procesa.test/cobros", "CHIBCHA", cliente_http(manejador))
    assert isinstance(adaptador, PasarelaPago) and adaptador.codigo_comercio == "CHIBCHA"
    assert adaptador.cobrar(tarjeta(codigo=None), Decimal("54.00")) == "PROC-77"
    assert recibidas[0] == {
        "codigoComercio": "CHIBCHA",
        "numero": "4242424242424242",
        "vencimiento": "2030-12",
        "franquicia": "VISA",
        "monto": "54.00",
        "moneda": "USD",
    }


def test_procesador_rechazos_y_fallas():
    def con(respuesta):
        return AdaptadorProcesadorPagos("https://p.test", "C", cliente_http(lambda p: respuesta))

    assert con(httpx.Response(200, json={"aprobado": False})).cobrar(tarjeta(), Decimal("1")) == ""
    assert con(httpx.Response(402)).cobrar(tarjeta(), Decimal("1")) == ""
    with pytest.raises(httpx.HTTPStatusError):
        con(httpx.Response(503)).cobrar(tarjeta(), Decimal("1"))
    with pytest.raises(ValidacionError):
        AdaptadorProcesadorPagos("https://p.test", "")


def test_el_cobro_fallido_del_procesador_deja_el_pago_fallido(cliente_de_prueba=None):
    """Integración con el dominio: una falla de red en el procesador es un pago FALLIDO (RN-03)."""
    from chibchaweb.dominio.cuentas import Cliente, Direccion
    from chibchaweb.dominio.facturacion import EstadoPago
    from chibchaweb.dominio.hospedaje import Plataforma, SitioWeb, Suscripcion

    def sin_red(peticion):
        raise httpx.ConnectError("sin red", request=peticion)

    cliente = Cliente(
        "Laura", "laura@correo.co", "300", Direccion("a", "b", "110111"), Direccion("c", "d", "110231"), tarjeta(), id=1
    )
    catalogo = falsos.RepositorioCatalogoEnMemoria()
    s = Suscripcion(
        cliente,
        SitioWeb("a.chibchaweb.com", Plataforma.UNIX),
        catalogo.buscar_paquete(1),
        catalogo.buscar_plan(1),
        date(2026, 11, 16),
    )
    pago = s.cobrar(AdaptadorProcesadorPagos("https://p.test", "C", cliente_http(sin_red)))
    assert pago.estado is EstadoPago.FALLIDO and s.fecha_corte == date(2026, 11, 16)


# --- Registrador de dominios ---------------------------------------------------------------------------


def test_registrador_transmite_el_xml():
    recibidas = []

    def manejador(peticion):
        recibidas.append(peticion)
        return httpx.Response(202)

    AdaptadorRegistradorDominio("https://registra.test/solicitudes", cliente_http(manejador)).enviar("<x>ñ</x>")
    assert recibidas[0].content == "<x>ñ</x>".encode()
    assert recibidas[0].headers["content-type"].startswith("application/xml")


def test_registrador_falla_si_el_servicio_falla():
    with pytest.raises(httpx.HTTPStatusError):
        AdaptadorRegistradorDominio("https://r.test", cliente_http(lambda p: httpx.Response(500))).enviar("<x/>")

    def sin_red(peticion):
        raise httpx.ConnectError("sin red", request=peticion)

    with pytest.raises(httpx.ConnectError):
        AdaptadorRegistradorDominio("https://r.test", cliente_http(sin_red)).enviar("<x/>")


# --- Sistema legado ------------------------------------------------------------------------------------


def test_legado_lee_las_exportaciones_del_directorio(tmp_path):
    (tmp_path / "clientes.csv").write_text("id,nombre\n\n# comentario\nC1,Ana\nC2,Luis\n", encoding="utf-8")
    (tmp_path / "hosting.csv").write_text("id,idCliente\nH1,C1\n", encoding="utf-8")
    (tmp_path / "pagos.csv").write_text("id\n", encoding="utf-8")
    adaptador = AdaptadorSistemaLegado(str(tmp_path))
    assert isinstance(adaptador, FuenteLegada) and adaptador.origen_datos == str(tmp_path)
    assert adaptador.leer_registros() == ["CLIENTE|C1,Ana", "CLIENTE|C2,Luis", "HOSTING|H1,C1"]
    with pytest.raises(ValidacionError):
        AdaptadorSistemaLegado("  ")
    with pytest.raises(ReglaNegocioError):
        AdaptadorSistemaLegado(str(tmp_path / "no-existe")).leer_registros()


def test_el_contenedor_con_externos_reales_construye_los_adaptadores_reales(settings, monkeypatch):
    from config import contenedor as modulo

    settings.SIMULAR_EXTERNOS = False
    settings.OIDC_CLIENT_ID = "app"
    settings.OIDC_CLIENT_SECRET = "secreto"
    settings.OIDC_REDIRECT_URI = "http://localhost:4200/auth/callback"
    settings.URL_VALIDADOR_TARJETA = "https://v.test"
    settings.URL_PROCESADOR_PAGOS = "https://p.test"
    settings.URL_REGISTRADOR_DOMINIOS = "https://r.test"
    proveedor, validador, pasarela, registrador, fuente = modulo._construir_adaptadores()
    assert isinstance(proveedor, AdaptadorOAuth) and proveedor.url_proveedor == "https://accounts.google.com"
    assert isinstance(validador, AdaptadorValidadorTarjeta) and isinstance(pasarela, AdaptadorProcesadorPagos)
    assert isinstance(registrador, AdaptadorRegistradorDominio) and isinstance(fuente, AdaptadorSistemaLegado)


def test_oauth_exige_secreto_y_uri_de_redireccion():
    with pytest.raises(ValidacionError):
        AdaptadorOAuth(PROVEEDOR, APP, "", "http://localhost/cb")
    with pytest.raises(ValidacionError):
        AdaptadorOAuth(PROVEEDOR, APP, "secreto", "")


@pytest.mark.parametrize(
    "configuracion",
    [
        {"issuer": "https://otro.test"},
        {"token_endpoint": "http://proveedor.test/token"},
        {"jwks_uri": "http://proveedor.test/jwks"},
    ],
)
def test_oauth_rechaza_descubrimiento_con_otro_emisor_o_sin_https(configuracion):
    servidor = ProveedorOidcFalso()
    original = servidor.__call__

    def con_configuracion(peticion):
        if peticion.url.path == "/.well-known/openid-configuration":
            base = {"issuer": PROVEEDOR, "token_endpoint": f"{PROVEEDOR}/token", "jwks_uri": f"{PROVEEDOR}/jwks"}
            return httpx.Response(200, json=base | configuracion)
        return original(peticion)

    adaptador = AdaptadorOAuth(PROVEEDOR, APP, "secreto", "http://localhost/cb", httpx.MockTransport(con_configuracion))
    with pytest.raises(AutorizacionFallidaError):
        adaptador.autorizar("c")
