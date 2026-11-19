"""Conformidad estructural con docs/modelo/dominio.md: clases, herencia, métodos y enumeraciones."""

import enum
import inspect
from abc import ABC

import pytest

from chibchaweb.dominio import (
    cuentas,
    dominios_web,
    errores,
    facturacion,
    hospedaje,
    integraciones,
    migracion,
    repositorios,
    respaldo,
    soporte,
)

# (módulo, clase, base del modelo o None, métodos públicos del modelo)
CLASES = [
    (cuentas, "Usuario", None, ["es_autenticable", "vincular_cuenta", "inactivar"]),
    (
        cuentas,
        "Cliente",
        "Usuario",
        [
            "es_autenticable",
            "asociar_distribuidor",
            "validar_datos_facturacion",
            "agregar_suscripcion",
            "cancelar_suscripcion",
        ],
    ),
    (cuentas, "Empleado", "Usuario", ["es_autenticable", "cambiar_rol", "puede_realizar"]),
    (
        cuentas,
        "Distribuidor",
        "Usuario",
        ["es_autenticable", "agregar_referido", "cantidad_referidos", "agregar_comision", "determinar_categoria"],
    ),
    (cuentas, "CuentaAcceso", None, ["coincide_con", "registrar_acceso"]),
    (cuentas, "Rol", None, ["otorgar", "revocar", "permite"]),
    (cuentas, "Direccion", None, ["validar"]),
    (cuentas, "MedioPago", None, ["validar", "esta_vigente", "descripcion"]),
    (cuentas, "TarjetaCredito", "MedioPago", ["validar", "esta_vigente", "descripcion"]),
    (cuentas, "Franquicia", None, ["reconoce_numero"]),
    (hospedaje, "PaqueteHosting", None, ["calcular_monto"]),
    (hospedaje, "PlanPago", None, ["aplicar_descuento"]),
    (hospedaje, "SitioWeb", None, ["asignar_dominio_propio", "tiene_dominio_propio"]),
    (
        hospedaje,
        "Suscripcion",
        None,
        [
            "monto_del_periodo",
            "esta_vencida",
            "avanzar_corte",
            "cambiar_paquete",
            "cambiar_plan",
            "agregar_pago",
            "suspender",
            "cobrar",
        ],
    ),
    (facturacion, "Pago", None, ["es_exitoso", "esta_disponible_para_comision", "marcar_comisionado"]),
    (facturacion, "Comision", None, ["agregar_pago_base", "calcular_monto", "asociar_cheque", "tiene_cheque"]),
    (facturacion, "Cheque", None, ["monto_en_letras"]),
    (facturacion, "CategoriaDistribuidor", None, ["nombre", "porcentaje", "aplica_a"]),
    (facturacion, "CategoriaBasica", "CategoriaDistribuidor", ["nombre", "porcentaje", "aplica_a"]),
    (facturacion, "CategoriaPremium", "CategoriaDistribuidor", ["nombre", "porcentaje", "aplica_a"]),
    (
        dominios_web,
        "SolicitudDominio",
        None,
        ["nombre_completo", "validar_formato", "esta_pendiente", "construir_documento", "enviar_a"],
    ),
    (
        dominios_web,
        "ConstructorSolicitud",
        None,
        ["iniciar_documento", "agregar_solicitante", "agregar_dominio", "agregar_fecha", "obtener_resultado"],
    ),
    (
        dominios_web,
        "ConstructorXML",
        "ConstructorSolicitud",
        ["iniciar_documento", "agregar_solicitante", "agregar_dominio", "agregar_fecha", "obtener_resultado"],
    ),
    (soporte, "Ticket", None, ["escalar", "resolver", "esta_abierto", "ultimo_movimiento"]),
    (soporte, "MovimientoTicket", None, ["resulta_en_resolucion"]),
    (soporte, "NivelServicio", None, ["puede_escalar", "precede"]),
    (
        migracion,
        "ProcesoMigracion",
        None,
        [
            "simular",
            "agregar_entrada",
            "cantidad_validos",
            "cantidad_invalidos",
            "aprobar",
            "cancelar",
            "puede_ejecutarse",
            "marcar_ejecutado",
            "marcar_revertido",
            "preparar_ejecucion",
        ],
    ),
    (migracion, "EntradaLog", None, ["es_error"]),
    (migracion, "RegistroLegado", None, ["validar", "describir_errores"]),
    (migracion, "ClienteLegado", "RegistroLegado", ["validar", "a_cliente"]),
    (migracion, "HostingLegado", "RegistroLegado", ["validar", "a_suscripcion"]),
    (migracion, "PagoLegado", "RegistroLegado", ["validar", "a_pago"]),
    (migracion, "CreadorRegistroLegado", None, ["tipo", "crear_registro", "procesar"]),
    (migracion, "CreadorClienteLegado", "CreadorRegistroLegado", ["tipo", "crear_registro"]),
    (migracion, "CreadorHostingLegado", "CreadorRegistroLegado", ["tipo", "crear_registro"]),
    (migracion, "CreadorPagoLegado", "CreadorRegistroLegado", ["tipo", "crear_registro"]),
    (integraciones, "ProveedorAutenticacion", None, ["autorizar"]),
    (integraciones, "IdentidadExterna", None, ["puede_prellenar_registro"]),
    (integraciones, "ValidadorMedioPago", None, ["verificar"]),
    (integraciones, "PasarelaPago", None, ["cobrar"]),
    (integraciones, "RegistradorDominio", None, ["enviar"]),
    (integraciones, "FuenteLegada", None, ["leer_registros"]),
    (
        respaldo,
        "GestorContingencia",
        None,
        ["cambiar_algoritmo", "cambiar_medio", "respaldar", "recuperar_pendientes", "confirmar_sincronizacion"],
    ),
    (respaldo, "AlgoritmoCifrado", None, ["nombre", "cifrar", "descifrar"]),
    (respaldo, "CifradoAES", "AlgoritmoCifrado", ["nombre", "cifrar", "descifrar"]),
    (respaldo, "CifradoChaCha20", "AlgoritmoCifrado", ["nombre", "cifrar", "descifrar"]),
    (respaldo, "CifradoCamellia", "AlgoritmoCifrado", ["nombre", "cifrar", "descifrar"]),
    (respaldo, "CifradoTwofish", "AlgoritmoCifrado", ["nombre", "cifrar", "descifrar"]),
    (respaldo, "MedioRespaldo", None, ["escribir", "leer_pendientes", "disponible", "limpiar"]),
    (respaldo, "ArchivoPlano", "MedioRespaldo", ["escribir", "leer_pendientes", "disponible", "limpiar"]),
]

ABSTRACTAS = {
    "Usuario": {"es_autenticable"},
    "MedioPago": {"validar", "esta_vigente", "descripcion"},
    "CategoriaDistribuidor": {"nombre", "porcentaje", "aplica_a"},
    "ConstructorSolicitud": {
        "iniciar_documento",
        "agregar_solicitante",
        "agregar_dominio",
        "agregar_fecha",
        "obtener_resultado",
    },
    "RegistroLegado": {"validar"},
    "CreadorRegistroLegado": {"tipo", "crear_registro"},
    "ProveedorAutenticacion": {"autorizar"},
    "ValidadorMedioPago": {"verificar"},
    "PasarelaPago": {"cobrar"},
    "RegistradorDominio": {"enviar"},
    "FuenteLegada": {"leer_registros"},
    "AlgoritmoCifrado": {"nombre", "cifrar", "descifrar"},
    "MedioRespaldo": {"escribir", "leer_pendientes", "disponible", "limpiar"},
}

ENUMERACIONES = [
    (hospedaje, "Plataforma", ["WINDOWS", "UNIX"]),
    (facturacion, "EstadoPago", ["EXITOSO", "FALLIDO"]),
    (dominios_web, "EstadoSolicitud", ["REGISTRADA", "ENVIADA", "FALLIDA"]),
    (soporte, "CategoriaTicket", ["RENDIMIENTO", "CORREO", "BASE_DATOS", "DOMINIO", "OTRA"]),
    (soporte, "EstadoTicket", ["ABIERTO", "ESCALADO", "RESUELTO"]),
    (migracion, "EstadoMigracion", ["CREADA", "SIMULADA", "APROBADA", "EJECUTADA", "REVERTIDA", "CANCELADA"]),
    (migracion, "NivelLog", ["INFO", "ADVERTENCIA", "ERROR"]),
]


@pytest.mark.parametrize(("modulo", "nombre", "base", "metodos"), CLASES, ids=[c[1] for c in CLASES])
def test_clase_del_modelo(modulo, nombre, base, metodos):
    clase = getattr(modulo, nombre)
    if base:
        assert getattr(modulo, base) in clase.__mro__[1:]
    for metodo in metodos:
        assert callable(getattr(clase, metodo, None)), f"{nombre}.{metodo}"
    assert getattr(clase, "__abstractmethods__", frozenset()) == ABSTRACTAS.get(nombre, frozenset())
    if nombre in ABSTRACTAS:
        assert issubclass(clase, ABC)


@pytest.mark.parametrize(("modulo", "nombre", "literales"), ENUMERACIONES, ids=[e[1] for e in ENUMERACIONES])
def test_enumeraciones(modulo, nombre, literales):
    clase = getattr(modulo, nombre)
    assert issubclass(clase, enum.Enum) and [m.name for m in clase] == literales


def test_metodos_privados_del_modelo():
    assert hasattr(dominios_web.SolicitudDominio, "_marcar_enviada")
    assert hasattr(dominios_web.SolicitudDominio, "_marcar_fallida")
    assert not hasattr(dominios_web.SolicitudDominio, "marcar_enviada")


def test_repositorios_tienen_los_metodos_del_modelo():
    esperado = {
        "RepositorioUsuario": {
            "insertar",
            "actualizar",
            "buscar_por_id",
            "buscar_por_filtro",
            "buscar_por_identificador_externo",
            "buscar_distribuidor_por_codigo",
            "inactivar",
            "buscar_por_correo",
            "buscar_clientes",
            "buscar_empleados",
            "buscar_distribuidores",
            "restaurar",
        },
        "RepositorioSuscripcion": {
            "insertar",
            "actualizar",
            "buscar_por_id",
            "buscar_por_filtro",
            "buscar_vencidas",
            "registrar_pago",
            "buscar_pagos_para_comision",
            "buscar_sitio",
            "restaurar",
        },
        "RepositorioComision": {
            "insertar",
            "actualizar",
            "buscar_por_id",
            "buscar_por_filtro",
            "registrar_cheque",
            "restaurar",
        },
        "RepositorioSolicitudDominio": {
            "insertar",
            "actualizar",
            "buscar_por_id",
            "buscar_por_filtro",
            "buscar_por_solicitante",
            "restaurar",
        },
        "RepositorioTicket": {
            "insertar",
            "actualizar",
            "buscar_por_id",
            "buscar_por_filtro",
            "buscar_creados_el",
            "buscar_abiertos",
            "buscar_por_reportante",
        },
        "RepositorioMigracion": {"insertar", "actualizar", "buscar_por_id", "buscar_por_filtro"},
        "RepositorioCatalogo": {
            "listar_paquetes",
            "buscar_paquete",
            "listar_planes",
            "buscar_plan",
            "listar_franquicias",  # P-17
            "buscar_franquicia",
            "buscar_rol",
            "buscar_nivel_inicial",
            "buscar_nivel_siguiente",
            "listar_roles",
        },
        "UnidadDeTrabajo": {"iniciar", "confirmar", "revertir"},
    }
    for nombre, metodos in esperado.items():
        assert getattr(repositorios, nombre).__abstractmethods__ == metodos, nombre


def test_errores_del_dominio():
    for nombre in (
        "ValidacionError",
        "ReglaNegocioError",
        "EstadoInvalidoError",
        "NoEncontradoError",
        "DuplicadoError",
        "ContingenciaActivaError",
    ):
        assert issubclass(getattr(errores, nombre), errores.ErrorDominio)
    e = errores.DuplicadoError("correo", "El correo ya existe")
    assert (e.campo, e.mensaje, str(e)) == ("correo", "El correo ya existe", "El correo ya existe")


def test_ningun_modulo_del_dominio_importa_django():
    import sys

    from chibchaweb import dominio

    for nombre, modulo in list(sys.modules.items()):
        if nombre.startswith("chibchaweb.dominio") and modulo is not None:
            fuente = inspect.getsource(modulo)
            assert "import django" not in fuente and "from django" not in fuente, nombre
    assert dominio.__doc__
