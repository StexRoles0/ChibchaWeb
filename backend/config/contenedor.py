"""Composition root (D-02): único lugar que conoce todas las capas.

Construye el gestor de contingencia (uno por proceso), los mapeadores, los adaptadores (reales o simulados según
``SIMULAR_EXTERNOS``) y la unidad de trabajo. Los 11 ``Servicio*`` se arman en ``contenedor()`` con esas dependencias.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

import httpx
from django.conf import settings

from chibchaweb.adaptadores.legado import AdaptadorSistemaLegado
from chibchaweb.adaptadores.oauth import AdaptadorOAuth
from chibchaweb.adaptadores.pagos import AdaptadorProcesadorPagos, AdaptadorValidadorTarjeta
from chibchaweb.adaptadores.registrador import AdaptadorRegistradorDominio
from chibchaweb.adaptadores.simulados import (
    FuenteLegadaSimulada,
    PasarelaPagoSimulada,
    ProveedorAutenticacionSimulado,
    RegistradorDominioSimulado,
    ValidadorMedioPagoSimulado,
)
from chibchaweb.dominio.dominios_web import ConstructorXML
from chibchaweb.dominio.facturacion import CategoriaBasica, CategoriaPremium
from chibchaweb.dominio.integraciones import (
    FuenteLegada,
    PasarelaPago,
    ProveedorAutenticacion,
    RegistradorDominio,
    ValidadorMedioPago,
)
from chibchaweb.dominio.migracion import (
    CreadorClienteLegado,
    CreadorHostingLegado,
    CreadorPagoLegado,
    CreadorRegistroLegado,
)
from chibchaweb.dominio.repositorios import (
    RepositorioCatalogo,
    RepositorioComision,
    RepositorioMigracion,
    RepositorioSolicitudDominio,
    RepositorioSuscripcion,
    RepositorioTicket,
    RepositorioUsuario,
    UnidadDeTrabajo,
)
from chibchaweb.dominio.respaldo import (
    ArchivoPlano,
    CifradoAES,
    CifradoCamellia,
    CifradoChaCha20,
    CifradoTwofish,
    GestorContingencia,
)
from chibchaweb.persistencia.mapeadores import (
    MapeadorCatalogo,
    MapeadorComision,
    MapeadorMigracion,
    MapeadorSolicitudDominio,
    MapeadorSuscripcion,
    MapeadorTicket,
    MapeadorUsuario,
)
from chibchaweb.persistencia.transacciones import UnidadDeTrabajoDjango
from chibchaweb.servicio.servicios import (
    ServicioAcceso,
    ServicioClientes,
    ServicioComisiones,
    ServicioConsultas,
    ServicioContingencia,
    ServicioDistribuidores,
    ServicioDominios,
    ServicioEmpleados,
    ServicioFacturacion,
    ServicioMigracion,
    ServicioSoporte,
)

_SUFIJO_DESCUBRIMIENTO = "/.well-known/openid-configuration"


@dataclass(frozen=True)
class Contenedor:
    """Dependencias ya armadas y los 11 servicios (``servicio_*``)."""

    gestor: GestorContingencia
    usuarios: RepositorioUsuario
    suscripciones: RepositorioSuscripcion
    comisiones: RepositorioComision
    solicitudes: RepositorioSolicitudDominio
    tickets: RepositorioTicket
    migraciones: RepositorioMigracion
    catalogo: RepositorioCatalogo
    unidad_de_trabajo: UnidadDeTrabajo
    proveedor_autenticacion: ProveedorAutenticacion
    validador_medio_pago: ValidadorMedioPago
    pasarela_pago: PasarelaPago
    registrador_dominio: RegistradorDominio
    fuente_legada: FuenteLegada
    creadores_migracion: Sequence[CreadorRegistroLegado]
    servicio_acceso: ServicioAcceso
    servicio_clientes: ServicioClientes
    servicio_empleados: ServicioEmpleados
    servicio_distribuidores: ServicioDistribuidores
    servicio_consultas: ServicioConsultas
    servicio_facturacion: ServicioFacturacion
    servicio_dominios: ServicioDominios
    servicio_comisiones: ServicioComisiones
    servicio_soporte: ServicioSoporte
    servicio_migracion: ServicioMigracion
    servicio_contingencia: ServicioContingencia


class _CreadoresPerezosos(Sequence):
    """Los creadores de registros legados validan contra el catálogo actual (P-12), que está en la BD.

    Se crean la primera vez que se usan para que armar el contenedor no necesite la BD: así la aplicación
    arranca y puede entrar en contingencia aunque la BD esté caída (RT04).
    """

    def __init__(self, catalogo: RepositorioCatalogo):
        self._catalogo = catalogo
        self._creadores: list[CreadorRegistroLegado] | None = None

    def _crear(self) -> list[CreadorRegistroLegado]:
        if self._creadores is None:
            self._creadores = [
                CreadorClienteLegado(self._catalogo.listar_franquicias()),
                CreadorHostingLegado(self._catalogo.listar_paquetes(), self._catalogo.listar_planes()),
                CreadorPagoLegado(),
            ]
        return self._creadores

    def __getitem__(self, indice):
        return self._crear()[indice]

    def __len__(self) -> int:
        return len(self._crear())


def construir_gestor() -> GestorContingencia:
    """Un solo gestor por proceso: algoritmo según ``ALGORITMO_CIFRADO``, clave ``CLAVE_CIFRADO``."""
    clave = base64.b64decode(settings.CLAVE_CIFRADO)
    algoritmos = [CifradoAES(clave), CifradoChaCha20(clave), CifradoCamellia(clave), CifradoTwofish(clave)]
    return GestorContingencia(algoritmos, settings.ALGORITMO_CIFRADO, ArchivoPlano(settings.RUTA_RESPALDO))


def _construir_adaptadores() -> tuple[
    ProveedorAutenticacion, ValidadorMedioPago, PasarelaPago, RegistradorDominio, FuenteLegada
]:
    if settings.SIMULAR_EXTERNOS:
        return (
            ProveedorAutenticacionSimulado(),
            ValidadorMedioPagoSimulado(),
            PasarelaPagoSimulada(),
            RegistradorDominioSimulado(),
            FuenteLegadaSimulada(),
        )
    return (
        AdaptadorOAuth(
            settings.OIDC_DISCOVERY_URL.removesuffix(_SUFIJO_DESCUBRIMIENTO),
            settings.OIDC_CLIENT_ID,
            settings.OIDC_CLIENT_SECRET,
            settings.OIDC_REDIRECT_URI,
        ),
        AdaptadorValidadorTarjeta(settings.URL_VALIDADOR_TARJETA, httpx.Client(timeout=10.0)),
        AdaptadorProcesadorPagos(settings.URL_PROCESADOR_PAGOS, settings.CODIGO_COMERCIO, httpx.Client(timeout=10.0)),
        AdaptadorRegistradorDominio(settings.URL_REGISTRADOR_DOMINIOS, httpx.Client(timeout=10.0)),
        AdaptadorSistemaLegado(settings.ORIGEN_DATOS_LEGADO),
    )


@lru_cache
def contenedor() -> Contenedor:
    """Devuelve el contenedor único del proceso."""
    gestor = construir_gestor()
    catalogo = MapeadorCatalogo()
    creadores = _CreadoresPerezosos(catalogo)
    proveedor, validador, pasarela, registrador, fuente = _construir_adaptadores()
    usuarios = MapeadorUsuario(gestor)
    suscripciones = MapeadorSuscripcion(gestor)
    comisiones = MapeadorComision(gestor)
    solicitudes = MapeadorSolicitudDominio(gestor)
    tickets = MapeadorTicket(gestor)
    migraciones = MapeadorMigracion(creadores)
    unidad = UnidadDeTrabajoDjango()
    consultas = ServicioConsultas(usuarios, tickets)
    return Contenedor(
        gestor=gestor,
        usuarios=usuarios,
        suscripciones=suscripciones,
        comisiones=comisiones,
        solicitudes=solicitudes,
        tickets=tickets,
        migraciones=migraciones,
        catalogo=catalogo,
        unidad_de_trabajo=unidad,
        proveedor_autenticacion=proveedor,
        validador_medio_pago=validador,
        pasarela_pago=pasarela,
        registrador_dominio=registrador,
        fuente_legada=fuente,
        creadores_migracion=creadores,
        servicio_acceso=ServicioAcceso(proveedor, validador, usuarios, catalogo, suscripciones),
        servicio_clientes=ServicioClientes(validador, usuarios, catalogo, suscripciones),
        servicio_empleados=ServicioEmpleados(usuarios, catalogo),
        servicio_distribuidores=ServicioDistribuidores(usuarios),
        servicio_consultas=consultas,
        servicio_facturacion=ServicioFacturacion(pasarela, suscripciones),
        servicio_dominios=ServicioDominios(ConstructorXML(), registrador, solicitudes, usuarios),
        servicio_comisiones=ServicioComisiones(
            [CategoriaBasica(), CategoriaPremium()], comisiones, usuarios, suscripciones
        ),
        servicio_soporte=ServicioSoporte(consultas, usuarios, tickets, catalogo, suscripciones),
        servicio_migracion=ServicioMigracion(fuente, creadores, migraciones, usuarios, suscripciones, catalogo, unidad),
        servicio_contingencia=ServicioContingencia(gestor, usuarios, suscripciones, comisiones, solicitudes, unidad),
    )
