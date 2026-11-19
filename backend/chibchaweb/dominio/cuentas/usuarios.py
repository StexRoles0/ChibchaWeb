"""Cuentas y perfiles (DC-MDO-01): usuarios, cuenta de acceso y roles."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

from chibchaweb.dominio._comun import (
    PATRON_TELEFONO,
    ahora,
    es_correo,
    misma_entidad,
    propiedad_id,
    texto_obligatorio,
)
from chibchaweb.dominio.errores import (
    EstadoInvalidoError,
    NoEncontradoError,
    ReglaNegocioError,
    ValidacionError,
)

if TYPE_CHECKING:
    from chibchaweb.dominio.cuentas.medios_pago import Direccion, MedioPago
    from chibchaweb.dominio.facturacion import CategoriaDistribuidor, Comision
    from chibchaweb.dominio.hospedaje import Suscripcion
    from chibchaweb.dominio.integraciones import IdentidadExterna, ValidadorMedioPago

_PATRON_DOCUMENTO = re.compile(r"^[A-Za-z0-9-]{1,20}$")
_PATRON_CODIGO_DISTRIBUIDOR = re.compile(r"^DIS-[A-Z0-9]{6}$")  # RN-15
_PROVEEDOR_PREDETERMINADO = "Google"  # D-05


def _validar_correo(correo: str | None) -> str:
    valor = (correo or "").strip().lower()
    if not es_correo(valor):
        raise ValidacionError("correo", "El correo no es válido")
    return valor


def _validar_telefono(telefono: str | None) -> str:
    valor = (telefono or "").strip()
    if not PATRON_TELEFONO.match(valor):
        raise ValidacionError("telefono", "El teléfono solo admite dígitos y espacios (máx. 20)")
    return valor


def _validar_documento(documento: str | None) -> str:
    valor = (documento or "").strip()
    if not _PATRON_DOCUMENTO.match(valor):
        raise ValidacionError("documento", "El documento debe ser alfanumérico (máx. 20)")
    return valor


def _proveedor_de(identificador_externo: str) -> str:
    """Proveedor de la identidad (P-13): prefijo ``proveedor|sub`` si lo trae; si no, el predeterminado."""
    prefijo, separador, _ = identificador_externo.partition("|")
    return prefijo if separador and prefijo else _PROVEEDOR_PREDETERMINADO


# --------------------------------------------------------------------------------------------------
# Usuarios
# --------------------------------------------------------------------------------------------------


class Usuario(ABC):
    """Datos comunes de toda persona registrada (clientes, empleados y distribuidores)."""

    id = propiedad_id()
    # Empleado y Distribuidor dados de baja no se modifican (cambiar el correo de una baja lógica rompería la
    # unicidad); el cliente inactivo lo rechaza el servicio con UsuarioInactivoError (RN-09).
    _inactivo_inmodificable = False

    def __init__(
        self,
        nombre: str,
        correo: str,
        telefono: str,
        id: int | None = None,
        activo: bool = True,
        fecha_registro: datetime | None = None,
        fecha_modificacion: datetime | None = None,
        cuenta: CuentaAcceso | None = None,
    ):
        self._id = id
        self._nombre = texto_obligatorio(nombre, "nombre", 120)
        self._correo = _validar_correo(correo)
        self._telefono = _validar_telefono(telefono)
        self._activo = bool(activo)
        self._fecha_registro = fecha_registro or ahora()
        if self._fecha_registro > ahora():
            raise ValidacionError("fechaRegistro", "La fecha de registro no puede ser futura")
        self._fecha_modificacion = fecha_modificacion or self._fecha_registro
        if self._fecha_modificacion < self._fecha_registro:
            raise ValidacionError("fechaModificacion", "La fecha de modificación es anterior al registro")
        if cuenta is not None and cuenta.titular is not self:
            raise ValidacionError("cuenta", "La cuenta de acceso pertenece a otro usuario")
        self._cuenta = cuenta

    # --- getters / setters --------------------------------------------------------------------
    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        self._exigir_modificable()
        self._nombre = texto_obligatorio(valor, "nombre", 120)
        self._tocar()

    @property
    def correo(self) -> str:
        return self._correo

    @correo.setter
    def correo(self, valor: str) -> None:
        self._exigir_modificable()
        self._correo = _validar_correo(valor)
        self._tocar()

    @property
    def telefono(self) -> str:
        return self._telefono

    @telefono.setter
    def telefono(self, valor: str) -> None:
        self._exigir_modificable()
        self._telefono = _validar_telefono(valor)
        self._tocar()

    @property
    def activo(self) -> bool:
        return self._activo

    @property
    def fecha_registro(self) -> datetime:
        return self._fecha_registro

    @property
    def fecha_modificacion(self) -> datetime:
        return self._fecha_modificacion

    @property
    def cuenta(self) -> CuentaAcceso | None:
        return self._cuenta

    # --- métodos del modelo -------------------------------------------------------------------
    @abstractmethod
    def es_autenticable(self) -> bool:
        """Indica si el tipo de usuario puede ingresar al sistema."""

    def vincular_cuenta(self, identidad: IdentidadExterna) -> None:
        """Crea la CuentaAcceso con el identificador verificado (RN-06)."""
        if not self.es_autenticable():
            raise ReglaNegocioError("Este tipo de usuario no puede ingresar al sistema")
        if self._cuenta is not None:
            raise ReglaNegocioError("El usuario ya tiene una cuenta de acceso vinculada")
        self._cuenta = CuentaAcceso(
            identificador_externo=identidad.identificador_externo,
            proveedor=_proveedor_de(identidad.identificador_externo),
            titular=self,
        )
        self._tocar()

    def inactivar(self) -> None:
        """Baja lógica: activo = false (RN-09)."""
        self._activo = False
        self._tocar()

    # --- auxiliares ---------------------------------------------------------------------------
    def _exigir_modificable(self) -> None:
        if self._inactivo_inmodificable and not self._activo:
            raise EstadoInvalidoError("El usuario está inactivo y no admite cambios")

    def _tocar(self) -> None:
        self._fecha_modificacion = max(ahora(), self._fecha_registro)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self._id!r}, activo={self._activo})"


class Cliente(Usuario):
    """Usuario que contrata el hospedaje."""

    def __init__(
        self,
        nombre: str,
        correo: str,
        telefono: str,
        residencia: Direccion,
        facturacion: Direccion,
        medio_pago: MedioPago,
        id: int | None = None,
        activo: bool = True,
        fecha_registro: datetime | None = None,
        fecha_modificacion: datetime | None = None,
        cuenta: CuentaAcceso | None = None,
        distribuidor: Distribuidor | None = None,
        suscripciones: list[Suscripcion] | None = None,
    ):
        super().__init__(nombre, correo, telefono, id, activo, fecha_registro, fecha_modificacion, cuenta)
        self._validar_direcciones(residencia, facturacion)
        if medio_pago is None:
            raise ValidacionError("medioPago", "El medio de pago es obligatorio")
        self._residencia = residencia
        self._facturacion = facturacion
        self._medio_pago = medio_pago
        self._distribuidor = distribuidor
        self._suscripciones: list[Suscripcion] = list(suscripciones or [])

    @staticmethod
    def _validar_direcciones(residencia: Direccion | None, facturacion: Direccion | None) -> None:
        if residencia is None:
            raise ValidacionError("residencia", "La dirección de residencia es obligatoria")
        if facturacion is None:
            raise ValidacionError("facturacion", "La dirección de facturación es obligatoria")
        if residencia is facturacion:
            raise ValidacionError("facturacion", "La dirección de facturación debe ser distinta de la de residencia")

    # RN-05: el cliente no puede cambiar el correo verificado.
    @Usuario.correo.setter
    def correo(self, valor: str) -> None:
        if _validar_correo(valor) != self._correo:
            raise ReglaNegocioError("El cliente no puede cambiar su correo verificado")

    @property
    def residencia(self) -> Direccion:
        return self._residencia

    @residencia.setter
    def residencia(self, valor: Direccion) -> None:
        self._validar_direcciones(valor, self._facturacion)
        self._residencia = valor
        self._tocar()

    @property
    def facturacion(self) -> Direccion:
        return self._facturacion

    @facturacion.setter
    def facturacion(self, valor: Direccion) -> None:
        self._validar_direcciones(self._residencia, valor)
        self._facturacion = valor
        self._tocar()

    @property
    def medio_pago(self) -> MedioPago:
        return self._medio_pago

    @medio_pago.setter
    def medio_pago(self, valor: MedioPago) -> None:
        if valor is None:
            raise ValidacionError("medioPago", "El medio de pago es obligatorio")
        self._medio_pago = valor
        self._tocar()

    @property
    def distribuidor(self) -> Distribuidor | None:
        return self._distribuidor

    @property
    def suscripciones(self) -> tuple[Suscripcion, ...]:
        return tuple(self._suscripciones)

    def es_autenticable(self) -> bool:
        return True

    def asociar_distribuidor(self, distribuidor: Distribuidor) -> None:
        """Vincula al cliente con el distribuidor que lo refirió (RN-13)."""
        if not distribuidor.activo:
            raise ReglaNegocioError("El distribuidor no está activo")
        if self._distribuidor is not None and not misma_entidad(self._distribuidor, distribuidor):
            raise ReglaNegocioError("El cliente ya está asociado a otro distribuidor")
        self._distribuidor = distribuidor

    def validar_datos_facturacion(self, validador: ValidadorMedioPago) -> bool:
        """Valida las dos direcciones y delega en el medio de pago su validación (RF01, RN-10)."""
        if not self._residencia.validar():
            raise ValidacionError("residencia", "La dirección de residencia no es válida")
        if not self._facturacion.validar():
            raise ValidacionError("facturacion", "La dirección de facturación no es válida")
        return self._medio_pago.validar(validador)

    def agregar_suscripcion(self, suscripcion: Suscripcion) -> None:
        if suscripcion.titular is not self and not misma_entidad(suscripcion.titular, self):
            raise ReglaNegocioError("La suscripción pertenece a otro cliente")
        if any(misma_entidad(s, suscripcion) for s in self._suscripciones):
            return
        self._suscripciones.append(suscripcion)

    def cancelar_suscripcion(self, suscripcion: Suscripcion) -> None:
        """Suspende y retira la suscripción de la colección (RN-09)."""
        for actual in self._suscripciones:
            if misma_entidad(actual, suscripcion):
                actual.suspender()
                self._suscripciones.remove(actual)
                return
        raise NoEncontradoError("La suscripción no pertenece al cliente")


class Empleado(Usuario):
    """Usuario del personal interno; sus permisos dependen del rol."""

    _inactivo_inmodificable = True

    def __init__(
        self,
        nombre: str,
        correo: str,
        telefono: str,
        documento: str,
        rol: Rol,
        id: int | None = None,
        activo: bool = True,
        fecha_registro: datetime | None = None,
        fecha_modificacion: datetime | None = None,
        cuenta: CuentaAcceso | None = None,
    ):
        super().__init__(nombre, correo, telefono, id, activo, fecha_registro, fecha_modificacion, cuenta)
        self._documento = _validar_documento(documento)
        if rol is None:
            raise ValidacionError("rol", "El rol es obligatorio")
        self._rol = rol

    @property
    def documento(self) -> str:
        return self._documento

    @documento.setter
    def documento(self, valor: str) -> None:
        self._exigir_modificable()
        self._documento = _validar_documento(valor)
        self._tocar()

    @property
    def rol(self) -> Rol:
        return self._rol

    def es_autenticable(self) -> bool:
        return True

    def cambiar_rol(self, nuevo: Rol) -> None:
        self._exigir_modificable()
        if nuevo is None:
            raise ValidacionError("rol", "El rol es obligatorio")
        self._rol = nuevo
        self._tocar()

    def puede_realizar(self, operacion: str) -> bool:
        return self._rol.permite(operacion)


class Distribuidor(Usuario):
    """Usuario que refiere clientes a cambio de una comisión. No se autentica."""

    _inactivo_inmodificable = True

    def __init__(
        self,
        nombre: str,
        correo: str,
        telefono: str,
        documento: str,
        codigo: str,
        id: int | None = None,
        activo: bool = True,
        fecha_registro: datetime | None = None,
        fecha_modificacion: datetime | None = None,
        referidos: list[Cliente] | None = None,
        comisiones: list[Comision] | None = None,
    ):
        super().__init__(nombre, correo, telefono, id, activo, fecha_registro, fecha_modificacion, None)
        self._documento = _validar_documento(documento)
        codigo = (codigo or "").strip()
        if not _PATRON_CODIGO_DISTRIBUIDOR.match(codigo):
            raise ValidacionError("codigo", "El código debe tener la forma DIS- y 6 caracteres alfanuméricos")
        self._codigo = codigo
        self._referidos: list[Cliente] = list(referidos or [])
        self._comisiones: list[Comision] = list(comisiones or [])

    @property
    def documento(self) -> str:
        return self._documento

    @documento.setter
    def documento(self, valor: str) -> None:
        self._exigir_modificable()
        self._documento = _validar_documento(valor)
        self._tocar()

    @property
    def codigo(self) -> str:
        return self._codigo

    @property
    def referidos(self) -> tuple[Cliente, ...]:
        return tuple(self._referidos)

    @property
    def comisiones(self) -> tuple[Comision, ...]:
        return tuple(self._comisiones)

    def es_autenticable(self) -> bool:
        return False

    def agregar_referido(self, cliente: Cliente) -> None:
        if not any(misma_entidad(c, cliente) for c in self._referidos):
            self._referidos.append(cliente)

    def cantidad_referidos(self) -> int:
        return len(self._referidos)

    def agregar_comision(self, comision: Comision) -> None:
        if not any(misma_entidad(c, comision) for c in self._comisiones):
            self._comisiones.append(comision)

    def determinar_categoria(self, categorias: list[CategoriaDistribuidor]) -> CategoriaDistribuidor:
        """Recorre las estrategias y devuelve la que aplica a su cantidad de referidos (RN-19)."""
        if not categorias:
            raise ReglaNegocioError("Se necesita al menos una categoría de distribuidor")
        cantidad = self.cantidad_referidos()
        for categoria in categorias:
            if categoria.aplica_a(cantidad):
                return categoria
        raise ReglaNegocioError(f"Ninguna categoría aplica a {cantidad} referidos")


# --------------------------------------------------------------------------------------------------
# Cuenta de acceso y rol
# --------------------------------------------------------------------------------------------------


class CuentaAcceso:
    """Vínculo entre un usuario y su identidad en el proveedor OAuth 2.0 (RN-08)."""

    id = propiedad_id()

    def __init__(
        self,
        identificador_externo: str,
        proveedor: str,
        titular: Usuario,
        id: int | None = None,
        fecha_vinculacion: datetime | None = None,
        ultimo_acceso: datetime | None = None,
    ):
        self._id = id
        self._identificador_externo = texto_obligatorio(identificador_externo, "identificadorExterno", 255)
        self._proveedor = texto_obligatorio(proveedor, "proveedor", 50)
        if titular is None:
            raise ValidacionError("titular", "La cuenta necesita un titular")
        self._titular = titular
        self._fecha_vinculacion = fecha_vinculacion or ahora()
        self._ultimo_acceso = ultimo_acceso

    @property
    def identificador_externo(self) -> str:
        return self._identificador_externo

    @property
    def proveedor(self) -> str:
        return self._proveedor

    @property
    def fecha_vinculacion(self) -> datetime:
        return self._fecha_vinculacion

    @property
    def ultimo_acceso(self) -> datetime | None:
        return self._ultimo_acceso

    @property
    def titular(self) -> Usuario:
        return self._titular

    def coincide_con(self, identificador_externo: str) -> bool:
        return self._identificador_externo == (identificador_externo or "").strip()

    def registrar_acceso(self) -> None:
        self._ultimo_acceso = ahora()

    def __repr__(self) -> str:
        return f"CuentaAcceso(id={self._id!r}, proveedor={self._proveedor!r})"


class Rol:
    """Cargo de un empleado con sus operaciones permitidas."""

    id = propiedad_id()

    def __init__(self, nombre: str, id: int | None = None, operaciones: list[str] | None = None):
        self._id = id
        self._nombre = texto_obligatorio(nombre, "nombre", 40)
        self._operaciones: list[str] = []
        for operacion in operaciones or []:
            self.otorgar(operacion)

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def operaciones(self) -> tuple[str, ...]:
        return tuple(self._operaciones)

    def otorgar(self, operacion: str) -> None:
        operacion = texto_obligatorio(operacion, "operacion", 60)
        if operacion not in self._operaciones:
            self._operaciones.append(operacion)

    def revocar(self, operacion: str) -> None:
        if operacion in self._operaciones:
            self._operaciones.remove(operacion)

    def permite(self, operacion: str) -> bool:
        return operacion in self._operaciones

    def __repr__(self) -> str:
        return f"Rol(id={self._id!r}, nombre={self._nombre!r})"
