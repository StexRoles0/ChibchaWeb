"""Caída REAL de la BD (RT04, D-30): una base de datos aislada detrás de un proxy TCP que se puede cortar.

No se usa la BD de pruebas compartida ni la marca ``django_db``: la prueba corta la conexión de verdad (se cierran
los sockets y el puerto deja de aceptar conexiones), así que no puede ir dentro de la transacción que
pytest-django abre por cada prueba ni dejar datos en la BD que usan las demás. Se crea una base propia
(``<BD de pruebas>_caida``) con ``schema.sql`` + ``seed_dev.sql`` y se borra al terminar el módulo.
"""

import socket
import threading

import psycopg
import pytest
from django.db import connections
from psycopg import sql

from config.contenedor import contenedor
from tests.conftest import _DOCS


class ProxyTcp:
    """Reenvía 127.0.0.1:<puerto> -> PostgreSQL. ``cortar`` mata las conexiones y cierra el puerto."""

    def __init__(self, destino: tuple[str, int]):
        self._destino = destino
        self.puerto = 0
        self._servidor: socket.socket | None = None
        self._conexiones: list[socket.socket] = []
        self._candado = threading.Lock()

    def iniciar(self) -> None:
        servidor = socket.socket()
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind(("127.0.0.1", self.puerto))
        servidor.listen()
        self.puerto = servidor.getsockname()[1]
        self._servidor = servidor
        threading.Thread(target=self._aceptar, args=(servidor,), daemon=True).start()

    def _aceptar(self, servidor: socket.socket) -> None:
        while True:
            try:
                cliente, _ = servidor.accept()
                remoto = socket.create_connection(self._destino)
            except OSError:
                if servidor.fileno() == -1:
                    return
                continue
            with self._candado:
                self._conexiones += [cliente, remoto]
            for origen, destino in ((cliente, remoto), (remoto, cliente)):
                threading.Thread(target=self._bombear, args=(origen, destino), daemon=True).start()

    @staticmethod
    def _bombear(origen: socket.socket, destino: socket.socket) -> None:
        try:
            while datos := origen.recv(65536):
                destino.sendall(datos)
        except OSError:
            pass
        finally:
            for s in (origen, destino):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                s.close()

    def cortar(self) -> None:
        if self._servidor is not None:
            try:
                self._servidor.shutdown(socket.SHUT_RDWR)  # despierta el accept() bloqueado
            except OSError:
                pass
            self._servidor.close()
            self._servidor = None
        with self._candado:
            conexiones, self._conexiones = self._conexiones, []
        for s in conexiones:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            s.close()

    def restablecer(self) -> None:
        self.iniciar()  # mismo puerto: Django sigue apuntando a él


class BdCortable:
    """La BD aislada, alcanzable por el proxy. ``cortar`` y ``restablecer`` incluyen la conexión de Django."""

    def __init__(self, proxy: ProxyTcp):
        self._proxy = proxy

    def _soltar_conexion_de_django(self) -> None:
        try:
            connections["default"].close()
        except Exception:  # la conexión ya estaba rota
            connections["default"].connection = None

    def cortar(self) -> None:
        self._proxy.cortar()

    def restablecer(self) -> None:
        self._soltar_conexion_de_django()  # no reutilizar el socket muerto
        self._proxy.restablecer()


def _administrador(parametros: dict) -> psycopg.Connection:
    return psycopg.connect(
        dbname="postgres",
        user=parametros["USER"],
        password=parametros["PASSWORD"],
        host=parametros["HOST"] or "localhost",
        port=parametros["PORT"] or 5432,
        autocommit=True,
    )


@pytest.fixture(scope="module")
def base_aislada(django_db_blocker):
    """Crea la base aislada con el esquema y la semilla; devuelve su nombre.

    No pide ``django_db_setup`` a propósito: sin pruebas marcadas con ``django_db`` pytest-django no crea la BD de
    pruebas y ese fixture (que aplica el esquema) correría contra la BD de desarrollo.
    """
    parametros = dict(connections["default"].settings_dict)
    nombre = f"test_{parametros['NAME'].removeprefix('test_')}_caida"
    with _administrador(parametros) as admin:
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(nombre)))
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre)))
    with psycopg.connect(
        dbname=nombre,
        user=parametros["USER"],
        password=parametros["PASSWORD"],
        host=parametros["HOST"] or "localhost",
        port=parametros["PORT"] or 5432,
        autocommit=True,
    ) as bd:
        for archivo in ("schema.sql", "seed_dev.sql"):
            bd.execute((_DOCS / archivo).read_text(encoding="utf-8"))
    yield nombre
    with django_db_blocker.unblock():
        connections["default"].close()
    with _administrador(parametros) as admin:
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(nombre)))


@pytest.fixture
def bd(base_aislada, django_db_blocker, settings, tmp_path):
    """Apunta Django a la base aislada a través del proxy; la prueba decide cuándo cortar y restablecer."""
    settings.SIMULAR_EXTERNOS = True
    settings.RUTA_RESPALDO = str(tmp_path / "respaldo.log")
    conexion = connections["default"]
    original = {k: conexion.settings_dict[k] for k in ("NAME", "HOST", "PORT")}
    destino = (original["HOST"] or "localhost", int(original["PORT"] or 5432))
    proxy = ProxyTcp(destino)
    proxy.iniciar()
    with django_db_blocker.unblock():
        conexion.close()
        conexion.settings_dict.update(NAME=base_aislada, HOST="127.0.0.1", PORT=str(proxy.puerto))
        contenedor.cache_clear()
        try:
            yield BdCortable(proxy)
        finally:
            proxy.cortar()
            try:
                conexion.close()
            except Exception:
                conexion.connection = None
            conexion.settings_dict.update(original)
            contenedor.cache_clear()
