"""Los 11 servicios de la aplicación (DC-SRV-01). Solo dependen del dominio (D-01, P-02).

Cada servicio recibe por constructor repositorios (``Repositorio*``), interfaces de integración,
``GestorContingencia`` o ``UnidadDeTrabajo``; nunca mapeadores. La lógica de negocio vive en el dominio: el
servicio busca, delega, guarda y arma el DTO.

Es un paquete (el archivo pasaba de 600 líneas) que reexporta las clases: la ruta del modelo
``chibchaweb.servicio.servicios`` se mantiene. Las enumeraciones ``CategoriaPerfil`` y ``TipoEntidad`` se
definen en ``dto`` y se reexportan aquí.
"""

from chibchaweb.servicio.dto import CategoriaPerfil, TipoEntidad
from chibchaweb.servicio.servicios.acceso import ServicioAcceso
from chibchaweb.servicio.servicios.clientes import ServicioClientes
from chibchaweb.servicio.servicios.comisiones import ServicioComisiones
from chibchaweb.servicio.servicios.consultas import ServicioConsultas
from chibchaweb.servicio.servicios.contingencia import ServicioContingencia
from chibchaweb.servicio.servicios.distribuidores import ServicioDistribuidores
from chibchaweb.servicio.servicios.dominios import ServicioDominios
from chibchaweb.servicio.servicios.empleados import ServicioEmpleados
from chibchaweb.servicio.servicios.facturacion import ServicioFacturacion
from chibchaweb.servicio.servicios.migracion import ServicioMigracion
from chibchaweb.servicio.servicios.soporte import ServicioSoporte

__all__ = [
    "CategoriaPerfil",
    "ServicioAcceso",
    "ServicioClientes",
    "ServicioComisiones",
    "ServicioConsultas",
    "ServicioContingencia",
    "ServicioDistribuidores",
    "ServicioDominios",
    "ServicioEmpleados",
    "ServicioFacturacion",
    "ServicioMigracion",
    "ServicioSoporte",
    "TipoEntidad",
]
