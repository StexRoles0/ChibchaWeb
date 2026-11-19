"""Distribuidores (DIS): alta con código generado, modificación y baja lógica (CU-DIS-02..04)."""

from __future__ import annotations

import secrets
import string

from chibchaweb.dominio.cuentas import Distribuidor
from chibchaweb.dominio.errores import DuplicadoError, NoEncontradoError
from chibchaweb.dominio.repositorios import RepositorioUsuario
from chibchaweb.servicio.dto import DistribuidorDTO

_ALFABETO = string.ascii_uppercase + string.digits
_INTENTOS_CODIGO = 20


def _generar_codigo() -> str:
    """RN-15, P-16: ``DIS-`` + 6 caracteres alfanuméricos en mayúscula (el dominio valida el formato)."""
    return "DIS-" + "".join(secrets.choice(_ALFABETO) for _ in range(6))


class ServicioDistribuidores:
    """Administración de distribuidores (módulo DIS)."""

    def __init__(self, usuarios: RepositorioUsuario):
        self._usuarios = usuarios

    def crear_distribuidor(self, datos: DistribuidorDTO) -> int:
        """CU-DIS-02. Registra al distribuidor y le genera un código único (RN-15)."""
        for _ in range(_INTENTOS_CODIGO):
            distribuidor = Distribuidor(
                datos.nombre, datos.correo, datos.telefono, datos.documento, self._codigo_libre()
            )
            self._exigir_unicos(distribuidor, None)
            try:
                return self._usuarios.insertar(distribuidor)
            except DuplicadoError as error:
                if getattr(error, "campo", "") != "codigo":
                    raise  # solo se reintenta cuando otro proceso tomó el mismo código
        raise DuplicadoError("codigo", "No se pudo generar un código de distribuidor único")

    def modificar_distribuidor(self, id_distribuidor: int, datos: DistribuidorDTO) -> None:
        """CU-DIS-03. Actualiza los datos (el dominio rechaza a uno inactivo, 409); el código no cambia."""
        distribuidor = self._buscar(id_distribuidor)
        nuevo = Distribuidor(datos.nombre, datos.correo, datos.telefono, datos.documento, distribuidor.codigo)
        self._exigir_unicos(nuevo, distribuidor)
        distribuidor.nombre = nuevo.nombre
        distribuidor.correo = nuevo.correo
        distribuidor.telefono = nuevo.telefono
        distribuidor.documento = nuevo.documento
        self._usuarios.actualizar(distribuidor)

    def eliminar_distribuidor(self, id_distribuidor: int) -> None:
        """CU-DIS-04. Baja lógica (RN-09). Sobre un distribuidor inactivo es idempotente."""
        distribuidor = self._buscar(id_distribuidor)
        if not distribuidor.activo:
            return
        distribuidor.inactivar()
        self._usuarios.actualizar(distribuidor)

    # --- auxiliares ---------------------------------------------------------------------------
    def _buscar(self, id_distribuidor: int) -> Distribuidor:
        usuario = self._usuarios.buscar_por_id(id_distribuidor)
        if not isinstance(usuario, Distribuidor):
            raise NoEncontradoError(f"No existe el distribuidor {id_distribuidor}")
        return usuario

    def _codigo_libre(self) -> str:
        """Genera códigos hasta encontrar uno que ningún distribuidor (activo o no) tenga."""
        for _ in range(_INTENTOS_CODIGO):
            codigo = _generar_codigo()
            if not any(d.codigo == codigo for d in self._usuarios.buscar_distribuidores(codigo)):
                return codigo
        raise DuplicadoError("codigo", "No se pudo generar un código de distribuidor único")

    def _exigir_unicos(self, candidato: Distribuidor, actual: Distribuidor | None) -> None:
        id_actual = actual.id if actual is not None else None
        otro = self._usuarios.buscar_por_correo(candidato.correo)
        if otro is not None and otro.id != id_actual:
            raise DuplicadoError("correo", "Ya existe un usuario con ese correo")
        for existente in self._usuarios.buscar_distribuidores(candidato.documento):
            if existente.documento == candidato.documento and existente.id != id_actual:
                raise DuplicadoError("documento", "Ya existe un distribuidor con ese documento")
