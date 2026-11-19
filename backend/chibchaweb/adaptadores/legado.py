"""Adaptador del sistema legado: lee sus exportaciones CSV y las entrega como ``"<TIPO>|<línea CSV>"`` (P-12)."""

from __future__ import annotations

from pathlib import Path

from chibchaweb.adaptadores._http import exigir_texto
from chibchaweb.dominio.errores import ReglaNegocioError
from chibchaweb.dominio.integraciones import FuenteLegada

# Archivo de exportación de cada tipo de registro, en el orden en que se leen.
ARCHIVOS_LEGADOS = (("CLIENTE", "clientes.csv"), ("HOSTING", "hosting.csv"), ("PAGO", "pagos.csv"))


def leer_exportaciones(directorio: Path) -> list[str]:
    """Lee ``clientes.csv``, ``hosting.csv`` y ``pagos.csv``: omite el encabezado, las líneas vacías y los ``#``."""
    registros: list[str] = []
    for tipo, nombre in ARCHIVOS_LEGADOS:
        ruta = directorio / nombre
        if not ruta.is_file():
            raise ReglaNegocioError(f"No se encontró el archivo legado {nombre}")
        lineas = [
            linea.strip()
            for linea in ruta.read_text(encoding="utf-8").splitlines()
            if linea.strip() and not linea.lstrip().startswith("#")
        ]
        registros.extend(f"{tipo}|{linea}" for linea in lineas[1:])  # la primera línea es el encabezado
    return registros


class AdaptadorSistemaLegado(FuenteLegada):
    """``origen_datos`` es el directorio donde el sistema legado deja sus exportaciones CSV."""

    def __init__(self, origen_datos: str):
        self._origen_datos = exigir_texto(origen_datos, "origenDatos")

    @property
    def origen_datos(self) -> str:
        return self._origen_datos

    def leer_registros(self) -> list[str]:
        return leer_exportaciones(Path(self._origen_datos))
