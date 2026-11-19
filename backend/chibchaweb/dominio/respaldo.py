"""Respaldo y contingencia (RT04): gestor, estrategias de cifrado y medio de respaldo.

Único módulo del dominio que puede usar ``cryptography``. Formato de cada algoritmo (D-07, D-20):
``base64(nonce ‖ cifrado ‖ tag)``. Camellia y Twofish usan Encrypt-then-MAC con HMAC-SHA256 y
subclaves derivadas con HKDF-SHA256 de la clave de 32 bytes.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
from abc import ABC, abstractmethod
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from chibchaweb.dominio import _twofish
from chibchaweb.dominio.errores import ReglaNegocioError, ValidacionError

try:  # cryptography ≥ 43 movió Camellia a "decrepit"
    from cryptography.hazmat.decrepit.ciphers.algorithms import Camellia as _Camellia
except ImportError:  # pragma: no cover
    from cryptography.hazmat.primitives.ciphers.algorithms import Camellia as _Camellia

_TAM_TAG_HMAC = 32


# --------------------------------------------------------------------------------------------------
# Auxiliares privados
# --------------------------------------------------------------------------------------------------


def _exigir_clave(clave: bytes) -> bytes:
    if not isinstance(clave, bytes | bytearray) or len(clave) != 32:
        raise ValidacionError("clave", "La clave de cifrado debe tener 32 bytes")
    return bytes(clave)


def _derivar(clave: bytes, contexto: bytes) -> tuple[bytes, bytes]:
    """Deriva una subclave de cifrado y otra de autenticación (HKDF-SHA256)."""
    material = HKDF(algorithm=hashes.SHA256(), length=64, salt=None, info=contexto).derive(clave)
    return material[:32], material[32:]


def _a_texto(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")


def _de_texto(contenido: str, minimo: int) -> bytes:
    try:
        datos = base64.b64decode(contenido.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError, AttributeError) as exc:
        raise ReglaNegocioError("El contenido cifrado no es base64 válido") from exc
    if len(datos) < minimo:
        raise ReglaNegocioError("El contenido cifrado está incompleto")
    return datos


def _etiqueta(clave_mac: bytes, datos: bytes) -> bytes:
    return hmac.new(clave_mac, datos, hashlib.sha256).digest()


def _verificar_etiqueta(clave_mac: bytes, datos: bytes, tag: bytes) -> None:
    if not hmac.compare_digest(_etiqueta(clave_mac, datos), tag):
        raise ReglaNegocioError("El contenido cifrado fue alterado o la clave no corresponde")


def _abrir_aead(aead: AESGCM | ChaCha20Poly1305, contenido: str) -> str:
    datos = _de_texto(contenido, 12 + 16)
    try:
        return aead.decrypt(datos[:12], datos[12:], None).decode("utf-8")
    except InvalidTag as exc:
        raise ReglaNegocioError("El contenido cifrado fue alterado o la clave no corresponde") from exc


# --------------------------------------------------------------------------------------------------
# Estrategias de cifrado
# --------------------------------------------------------------------------------------------------


class AlgoritmoCifrado(ABC):
    """Estrategia de cifrado; el algoritmo activo se elige en tiempo de ejecución (Strategy)."""

    @abstractmethod
    def nombre(self) -> str:
        """Nombre del algoritmo."""

    @abstractmethod
    def cifrar(self, contenido: str) -> str:
        """Cifra el contenido."""

    @abstractmethod
    def descifrar(self, contenido: str) -> str:
        """Descifra el contenido."""


class CifradoAES(AlgoritmoCifrado):
    """AES-256-GCM."""

    def __init__(self, clave: bytes):
        self._aead = AESGCM(_derivar(_exigir_clave(clave), b"chibchaweb-aes")[0])

    def nombre(self) -> str:
        return "AES"

    def cifrar(self, contenido: str) -> str:
        nonce = os.urandom(12)
        return _a_texto(nonce + self._aead.encrypt(nonce, contenido.encode("utf-8"), None))

    def descifrar(self, contenido: str) -> str:
        return _abrir_aead(self._aead, contenido)


class CifradoChaCha20(AlgoritmoCifrado):
    """ChaCha20-Poly1305."""

    def __init__(self, clave: bytes):
        self._aead = ChaCha20Poly1305(_derivar(_exigir_clave(clave), b"chibchaweb-chacha20")[0])

    def nombre(self) -> str:
        return "ChaCha20"

    def cifrar(self, contenido: str) -> str:
        nonce = os.urandom(12)
        return _a_texto(nonce + self._aead.encrypt(nonce, contenido.encode("utf-8"), None))

    def descifrar(self, contenido: str) -> str:
        return _abrir_aead(self._aead, contenido)


class CifradoCamellia(AlgoritmoCifrado):
    """Camellia-256-CBC con relleno PKCS7 + HMAC-SHA256."""

    def __init__(self, clave: bytes):
        self._clave_cifrado, self._clave_mac = _derivar(_exigir_clave(clave), b"chibchaweb-camellia")

    def nombre(self) -> str:
        return "Camellia"

    def cifrar(self, contenido: str) -> str:
        iv = os.urandom(16)
        relleno = padding.PKCS7(128).padder()
        datos = relleno.update(contenido.encode("utf-8")) + relleno.finalize()
        cifrador = Cipher(_Camellia(self._clave_cifrado), modes.CBC(iv)).encryptor()
        cuerpo = iv + cifrador.update(datos) + cifrador.finalize()
        return _a_texto(cuerpo + _etiqueta(self._clave_mac, cuerpo))

    def descifrar(self, contenido: str) -> str:
        datos = _de_texto(contenido, 16 + 16 + _TAM_TAG_HMAC)
        cuerpo, tag = datos[:-_TAM_TAG_HMAC], datos[-_TAM_TAG_HMAC:]
        _verificar_etiqueta(self._clave_mac, cuerpo, tag)
        if (len(cuerpo) - 16) % 16:
            raise ReglaNegocioError("El contenido cifrado está incompleto")
        descifrador = Cipher(_Camellia(self._clave_cifrado), modes.CBC(cuerpo[:16])).decryptor()
        plano = descifrador.update(cuerpo[16:]) + descifrador.finalize()
        quitar = padding.PKCS7(128).unpadder()
        return (quitar.update(plano) + quitar.finalize()).decode("utf-8")


class CifradoTwofish(AlgoritmoCifrado):
    """Twofish-256-CTR + HMAC-SHA256 (bloque Twofish en Python puro, D-20)."""

    def __init__(self, clave: bytes):
        clave_cifrado, self._clave_mac = _derivar(_exigir_clave(clave), b"chibchaweb-twofish")
        self._clave = _twofish.ClaveTwofish(clave_cifrado)

    def nombre(self) -> str:
        return "Twofish"

    def cifrar(self, contenido: str) -> str:
        nonce = os.urandom(16)
        cuerpo = nonce + _twofish.flujo_ctr(self._clave, nonce, contenido.encode("utf-8"))
        return _a_texto(cuerpo + _etiqueta(self._clave_mac, cuerpo))

    def descifrar(self, contenido: str) -> str:
        datos = _de_texto(contenido, 16 + _TAM_TAG_HMAC)
        cuerpo, tag = datos[:-_TAM_TAG_HMAC], datos[-_TAM_TAG_HMAC:]
        _verificar_etiqueta(self._clave_mac, cuerpo, tag)
        return _twofish.flujo_ctr(self._clave, cuerpo[:16], cuerpo[16:]).decode("utf-8")


# --------------------------------------------------------------------------------------------------
# Medios de respaldo
# --------------------------------------------------------------------------------------------------


class MedioRespaldo(ABC):
    """Estrategia de almacenamiento de contingencia (Strategy)."""

    @abstractmethod
    def escribir(self, registro: str) -> None:
        """Escribe un registro."""

    @abstractmethod
    def leer_pendientes(self) -> list[str]:
        """Lee los registros pendientes."""

    @abstractmethod
    def disponible(self) -> bool:
        """Indica si el medio puede escribirse."""

    @abstractmethod
    def limpiar(self) -> None:
        """Elimina los registros sincronizados."""


class ArchivoPlano(MedioRespaldo):
    """Escribe una línea por evento en un archivo plano del volumen persistente."""

    def __init__(self, ruta: str):
        if not (ruta or "").strip():
            raise ValidacionError("ruta", "La ruta del archivo de respaldo es obligatoria")
        self._ruta = ruta

    @property
    def ruta(self) -> str:
        return self._ruta

    def escribir(self, registro: str) -> None:
        if "\n" in registro or "\r" in registro:
            raise ValidacionError("registro", "Un registro de respaldo no puede tener saltos de línea")
        ruta = Path(self._ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(ruta, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)  # solo el propietario
        with os.fdopen(descriptor, "a", encoding="utf-8") as archivo:
            archivo.write(registro + "\n")
            archivo.flush()
            os.fsync(archivo.fileno())

    def leer_pendientes(self) -> list[str]:
        ruta = Path(self._ruta)
        if not ruta.exists():
            return []
        return [linea for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.strip()]

    def disponible(self) -> bool:
        ruta = Path(self._ruta)
        if ruta.exists():
            return ruta.is_file() and os.access(ruta, os.W_OK)
        padre = ruta.parent
        while not padre.exists() and padre != padre.parent:
            padre = padre.parent
        return padre.is_dir() and os.access(padre, os.W_OK)

    def limpiar(self) -> None:
        ruta = Path(self._ruta)
        if ruta.exists():
            ruta.write_text("", encoding="utf-8")


# --------------------------------------------------------------------------------------------------
# Gestor
# --------------------------------------------------------------------------------------------------


class GestorContingencia:
    """Coordina el respaldo cifrado cuando la BD no está disponible (RT04)."""

    def __init__(self, algoritmos: list[AlgoritmoCifrado], algoritmo_activo: str, medio: MedioRespaldo):
        if not algoritmos:
            raise ValidacionError("algoritmos", "Se necesita al menos un algoritmo de cifrado")
        nombres = [a.nombre() for a in algoritmos]
        if len(set(nombres)) != len(nombres):
            raise ValidacionError("algoritmos", "Hay algoritmos con el mismo nombre")
        if medio is None:
            raise ValidacionError("medio", "El medio de respaldo es obligatorio")
        self._algoritmos: list[AlgoritmoCifrado] = list(algoritmos)
        self._algoritmo_activo = ""
        self._medio = medio
        self.cambiar_algoritmo(algoritmo_activo)

    @property
    def algoritmos(self) -> tuple[AlgoritmoCifrado, ...]:
        return tuple(self._algoritmos)

    @property
    def algoritmo_activo(self) -> str:
        return self._algoritmo_activo

    @property
    def medio(self) -> MedioRespaldo:
        return self._medio

    def cambiar_algoritmo(self, nombre: str) -> None:
        """RN-29: activa uno de los algoritmos disponibles en tiempo de ejecución."""
        self._algoritmo(nombre, "nombre")
        self._algoritmo_activo = nombre

    def cambiar_medio(self, medio: MedioRespaldo) -> None:
        if medio is None:
            raise ValidacionError("medio", "El medio de respaldo es obligatorio")
        self._medio = medio

    def respaldar(self, tipo_evento: str, contenido: str) -> None:
        """Escribe ``algoritmo|tipo_evento|cifrado(tipo_evento|contenido)`` con el algoritmo activo."""
        tipo = (tipo_evento or "").strip()
        if not tipo or any(c in tipo for c in "|\r\n"):
            raise ValidacionError("tipoEvento", "El tipo de evento es obligatorio y no admite '|' ni saltos")
        if not self._medio.disponible():
            raise ReglaNegocioError("El medio de respaldo no está disponible")
        algoritmo = self._algoritmo(self._algoritmo_activo, "algoritmoActivo")
        # El tipo viaja también dentro del texto cifrado para que no se pueda alterar en la línea.
        self._medio.escribir(f"{algoritmo.nombre()}|{tipo}|{algoritmo.cifrar(f'{tipo}|{contenido}')}")

    def recuperar_pendientes(self) -> list[str]:
        """Descifra cada registro con el algoritmo que lo cifró (RN-29), en el orden escrito (RN-30).

        Cada elemento devuelto tiene la forma ``tipo_evento|contenido`` (P-14).
        """
        pendientes = []
        for linea in self._medio.leer_pendientes():
            partes = linea.split("|", 2)
            if len(partes) != 3:
                raise ReglaNegocioError("Hay un registro de respaldo con formato inválido")
            nombre, tipo, cifrado = partes
            plano = self._algoritmo(nombre, "algoritmo").descifrar(cifrado)
            tipo_interno, separador, _ = plano.partition("|")
            if not separador or tipo_interno != tipo:
                raise ReglaNegocioError("El tipo de evento del respaldo fue alterado")
            pendientes.append(plano)
        return pendientes

    def confirmar_sincronizacion(self) -> None:
        """Vacía el medio una vez sincronizado."""
        self._medio.limpiar()

    def _algoritmo(self, nombre: str, campo: str) -> AlgoritmoCifrado:
        for algoritmo in self._algoritmos:
            if algoritmo.nombre() == nombre:
                return algoritmo
        raise ValidacionError(campo, f"El algoritmo {nombre!r} no está disponible")
