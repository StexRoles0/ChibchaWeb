"""Contingencia: RN-29 (algoritmos intercambiables) y apoyo del dominio a RN-30."""

import base64
import hashlib
import hmac
import os

import pytest

from chibchaweb.dominio.errores import ReglaNegocioError, ValidacionError
from chibchaweb.dominio.respaldo import (
    AlgoritmoCifrado,
    ArchivoPlano,
    CifradoAES,
    CifradoCamellia,
    CifradoChaCha20,
    CifradoTwofish,
    GestorContingencia,
    MedioRespaldo,
)

CLAVE = bytes(range(32))
CONTENIDO = '{"tipo": "Usuario", "nombre": "Laura Gómez", "nota": "ñandú €"}'
CLASES = [CifradoAES, CifradoChaCha20, CifradoCamellia, CifradoTwofish]


class MedioEnMemoria(MedioRespaldo):
    def __init__(self, disponible=True):
        self.lineas: list[str] = []
        self._disponible = disponible

    def escribir(self, registro):
        self.lineas.append(registro)

    def leer_pendientes(self):
        return list(self.lineas)

    def disponible(self):
        return self._disponible

    def limpiar(self):
        self.lineas.clear()


@pytest.fixture
def algoritmos():
    return [c(CLAVE) for c in CLASES]


@pytest.fixture
def medio():
    return MedioEnMemoria()


@pytest.fixture
def gestor(algoritmos, medio):
    return GestorContingencia(algoritmos, "AES", medio)


# --- Estrategias de cifrado --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("clase", "nombre", "minimo"),
    [
        (CifradoAES, "AES", 28),
        (CifradoChaCha20, "ChaCha20", 28),
        (CifradoCamellia, "Camellia", 64),
        (CifradoTwofish, "Twofish", 48),
    ],
)
def test_rn29_ida_y_vuelta_de_cada_algoritmo(clase, nombre, minimo):
    algoritmo = clase(CLAVE)
    assert isinstance(algoritmo, AlgoritmoCifrado) and algoritmo.nombre() == nombre
    cifrado = algoritmo.cifrar(CONTENIDO)
    assert CONTENIDO not in cifrado and len(base64.b64decode(cifrado)) >= minimo
    assert algoritmo.descifrar(cifrado) == CONTENIDO
    assert algoritmo.cifrar(CONTENIDO) != cifrado  # nonce aleatorio
    assert algoritmo.descifrar(algoritmo.cifrar("")) == ""


@pytest.mark.parametrize("clase", CLASES)
def test_rn29_detecta_alteraciones_y_clave_incorrecta(clase):
    algoritmo = clase(CLAVE)
    datos = bytearray(base64.b64decode(algoritmo.cifrar(CONTENIDO)))
    datos[-1] ^= 1
    with pytest.raises(ReglaNegocioError):
        algoritmo.descifrar(base64.b64encode(bytes(datos)).decode())
    with pytest.raises(ReglaNegocioError):
        clase(bytes(32)).descifrar(algoritmo.cifrar(CONTENIDO))
    with pytest.raises(ReglaNegocioError):
        algoritmo.descifrar("no es base64!!")
    with pytest.raises(ReglaNegocioError):
        algoritmo.descifrar(base64.b64encode(b"corto").decode())


def test_rn29_camellia_cuerpo_no_multiplo_de_bloque():
    camellia = CifradoCamellia(CLAVE)
    # tag correcto sobre un cuerpo de longitud inválida: debe fallar por formato, no por padding
    cuerpo = os.urandom(16 + 17)
    tag = hmac.new(camellia._clave_mac, cuerpo, hashlib.sha256).digest()
    with pytest.raises(ReglaNegocioError):
        camellia.descifrar(base64.b64encode(cuerpo + tag).decode())


@pytest.mark.parametrize("clase", CLASES)
def test_rn29_clave_debe_tener_32_bytes(clase):
    with pytest.raises(ValidacionError):
        clase(b"corta")
    with pytest.raises(ValidacionError):
        clase("x" * 32)


def test_algoritmo_cifrado_y_medio_son_interfaces():
    for clase in (AlgoritmoCifrado, MedioRespaldo):
        with pytest.raises(TypeError):
            clase()  # type: ignore[abstract]


# --- Gestor ------------------------------------------------------------------------------------


def test_rn29_respaldar_escribe_algoritmo_tipo_y_cifrado(gestor, medio):
    gestor.respaldar("Usuario.insertar", CONTENIDO)
    nombre, tipo, cifrado = medio.lineas[0].split("|", 2)
    assert (nombre, tipo) == ("AES", "Usuario.insertar") and CONTENIDO not in cifrado
    assert gestor.recuperar_pendientes() == [f"Usuario.insertar|{CONTENIDO}"]


def test_rn29_cambio_de_algoritmo_en_ejecucion_y_registros_anteriores(gestor, medio):
    for nombre in ("AES", "ChaCha20", "Camellia", "Twofish"):
        gestor.cambiar_algoritmo(nombre)
        assert gestor.algoritmo_activo == nombre
        gestor.respaldar(f"Evento.{nombre}", f"contenido {nombre}")
    assert [linea.split("|")[0] for linea in medio.lineas] == ["AES", "ChaCha20", "Camellia", "Twofish"]
    assert gestor.recuperar_pendientes() == [
        "Evento.AES|contenido AES",
        "Evento.ChaCha20|contenido ChaCha20",
        "Evento.Camellia|contenido Camellia",
        "Evento.Twofish|contenido Twofish",
    ]


def test_rn29_algoritmo_desconocido(gestor, medio, algoritmos):
    with pytest.raises(ValidacionError) as e:
        gestor.cambiar_algoritmo("DES")
    assert e.value.campo == "nombre" and gestor.algoritmo_activo == "AES"
    with pytest.raises(ValidacionError):
        GestorContingencia(algoritmos, "Blowfish", medio)
    medio.lineas.append("DES|Usuario.insertar|abc")
    with pytest.raises(ValidacionError):
        gestor.recuperar_pendientes()


def test_rn29_registro_de_respaldo_mal_formado(gestor, medio):
    medio.lineas.append("solo-una-parte")
    with pytest.raises(ReglaNegocioError):
        gestor.recuperar_pendientes()


def test_rn30_recupera_en_el_orden_escrito_y_confirmar_vacia(gestor, medio):
    for i in range(5):
        gestor.respaldar("Comision.insertar", f"#{i}")
    assert [p.split("|", 1)[1] for p in gestor.recuperar_pendientes()] == [f"#{i}" for i in range(5)]
    assert len(medio.lineas) == 5  # recuperar no vacía el medio
    gestor.confirmar_sincronizacion()
    assert gestor.recuperar_pendientes() == []


def test_gestor_validaciones(algoritmos, medio, gestor):
    with pytest.raises(ValidacionError):
        GestorContingencia([], "AES", medio)
    with pytest.raises(ValidacionError):
        GestorContingencia([CifradoAES(CLAVE), CifradoAES(CLAVE)], "AES", medio)
    with pytest.raises(ValidacionError):
        GestorContingencia(algoritmos, "AES", None)  # type: ignore[arg-type]
    for tipo in ("", "A|B", "A\nB"):
        with pytest.raises(ValidacionError):
            gestor.respaldar(tipo, "x")
    with pytest.raises(ValidacionError):
        gestor.cambiar_medio(None)  # type: ignore[arg-type]
    assert len(gestor.algoritmos) == 4 and gestor.medio is medio


def test_respaldar_con_medio_no_disponible(gestor):
    gestor.cambiar_medio(MedioEnMemoria(disponible=False))
    with pytest.raises(ReglaNegocioError):
        gestor.respaldar("Usuario.insertar", "x")


def test_cambiar_medio_en_ejecucion(gestor, medio):
    nuevo = MedioEnMemoria()
    gestor.cambiar_medio(nuevo)
    gestor.respaldar("Usuario.actualizar", "x")
    assert medio.lineas == [] and len(nuevo.lineas) == 1


def test_codigo_seguridad_no_se_respalda_si_el_mapeador_no_lo_incluye(gestor, medio):
    # El gestor solo escribe lo que recibe y cifrado: nunca texto en claro.
    gestor.respaldar("Usuario.insertar", '{"numero": "4242424242424242"}')
    assert "4242424242424242" not in medio.lineas[0]


# --- ArchivoPlano ------------------------------------------------------------------------------


def test_archivo_plano_escribe_lee_y_limpia(tmp_path):
    archivo = ArchivoPlano(str(tmp_path / "sub" / "respaldo.txt"))
    assert archivo.ruta.endswith("respaldo.txt")
    assert archivo.disponible() and archivo.leer_pendientes() == []
    archivo.escribir("AES|Usuario.insertar|abc")
    archivo.escribir("AES|Usuario.insertar|def")
    assert archivo.disponible()
    assert archivo.leer_pendientes() == ["AES|Usuario.insertar|abc", "AES|Usuario.insertar|def"]
    archivo.limpiar()
    assert archivo.leer_pendientes() == []
    ArchivoPlano(str(tmp_path / "no-existe.txt")).limpiar()


def test_archivo_plano_validaciones(tmp_path):
    with pytest.raises(ValidacionError):
        ArchivoPlano("  ")
    with pytest.raises(ValidacionError):
        ArchivoPlano(str(tmp_path / "r.txt")).escribir("a\nb")
    directorio = tmp_path / "es-directorio"
    directorio.mkdir()
    assert ArchivoPlano(str(directorio)).disponible() is False


def test_gestor_con_archivo_plano_de_punta_a_punta(tmp_path, algoritmos):
    gestor = GestorContingencia(algoritmos, "Twofish", ArchivoPlano(str(tmp_path / "respaldo.txt")))
    gestor.respaldar("SolicitudDominio.insertar", CONTENIDO)
    gestor.cambiar_algoritmo("Camellia")
    gestor.respaldar("Suscripcion.actualizar", "otro")
    assert gestor.recuperar_pendientes() == [f"SolicitudDominio.insertar|{CONTENIDO}", "Suscripcion.actualizar|otro"]


def test_rn29_tipo_de_evento_autenticado(gestor, medio):
    gestor.respaldar("Usuario.insertar", CONTENIDO)
    nombre, _, cifrado = medio.lineas[0].split("|", 2)
    medio.lineas[0] = f"{nombre}|Suscripcion.insertar|{cifrado}"
    with pytest.raises(ReglaNegocioError, match="alterado"):
        gestor.recuperar_pendientes()


def test_archivo_plano_se_crea_con_permisos_0600(tmp_path):
    ruta = tmp_path / "sub" / "respaldo.log"
    ArchivoPlano(str(ruta)).escribir("linea")
    assert (ruta.stat().st_mode & 0o777) == 0o600
