"""Empleados (EMP): alta, modificación y baja lógica (CU-EMP-02..04)."""

from __future__ import annotations

from chibchaweb.dominio.cuentas import Empleado
from chibchaweb.dominio.errores import DuplicadoError, NoEncontradoError, ValidacionError
from chibchaweb.dominio.repositorios import RepositorioCatalogo, RepositorioUsuario
from chibchaweb.servicio.dto import EmpleadoDTO, ResumenDTO


class ServicioEmpleados:
    """Administración de empleados (módulo EMP)."""

    def __init__(self, usuarios: RepositorioUsuario, catalogo: RepositorioCatalogo):
        self._usuarios = usuarios
        self._catalogo = catalogo

    def consultar_roles(self) -> list[ResumenDTO]:
        """Cargos para el formulario de empleados."""
        return [ResumenDTO(r.id, r.nombre, "", "ACTIVO") for r in self._catalogo.listar_roles()]  # type: ignore[arg-type]

    def crear_empleado(self, datos: EmpleadoDTO) -> int:
        """CU-EMP-02. Registra un empleado con su rol; correo y documento son únicos (409 DUPLICADO)."""
        empleado = self._candidato(datos)  # el dominio valida nombre, correo, teléfono, documento y rol
        self._exigir_unicos(empleado, None)
        return self._usuarios.insertar(empleado)

    def modificar_empleado(self, id_empleado: int, datos: EmpleadoDTO) -> None:
        """CU-EMP-03. Actualiza los datos y el rol del empleado; el dominio rechaza a uno inactivo (409)."""
        empleado = self._buscar(id_empleado)
        nuevo = self._candidato(datos)  # valida todo antes de tocar al empleado real
        self._exigir_unicos(nuevo, empleado)
        empleado.nombre = nuevo.nombre
        empleado.correo = nuevo.correo
        empleado.telefono = nuevo.telefono
        empleado.documento = nuevo.documento
        empleado.cambiar_rol(nuevo.rol)
        self._usuarios.actualizar(empleado)

    def eliminar_empleado(self, id_empleado: int) -> None:
        """CU-EMP-04. Baja lógica (RN-09); nunca borra la fila. Sobre un inactivo es idempotente."""
        empleado = self._buscar(id_empleado)
        if not empleado.activo:
            return
        empleado.inactivar()
        self._usuarios.actualizar(empleado)

    # --- auxiliares ---------------------------------------------------------------------------
    def _buscar(self, id_empleado: int) -> Empleado:
        usuario = self._usuarios.buscar_por_id(id_empleado)
        if not isinstance(usuario, Empleado):
            raise NoEncontradoError(f"No existe el empleado {id_empleado}")
        return usuario

    def _candidato(self, datos: EmpleadoDTO) -> Empleado:
        try:
            rol = self._catalogo.buscar_rol(datos.id_rol)
        except NoEncontradoError:
            raise ValidacionError("idRol", "El cargo no existe") from None
        return Empleado(datos.nombre, datos.correo, datos.telefono, datos.documento, rol)

    def _exigir_unicos(self, candidato: Empleado, actual: Empleado | None) -> None:
        """El servicio comprueba antes de escribir; la restricción UNIQUE de la BD es la última barrera."""
        id_actual = actual.id if actual is not None else None
        otro = self._usuarios.buscar_por_correo(candidato.correo)
        if otro is not None and otro.id != id_actual:
            raise DuplicadoError("correo", "Ya existe un usuario con ese correo")
        for existente in self._usuarios.buscar_empleados(candidato.documento):
            if existente.documento == candidato.documento and existente.id != id_actual:
                raise DuplicadoError("documento", "Ya existe un empleado con ese documento")
