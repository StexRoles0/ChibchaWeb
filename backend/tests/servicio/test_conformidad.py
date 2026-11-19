"""Conformidad con docs/modelo/servicio.md: DTO, enumeraciones y constructores de los 11 servicios."""

import dataclasses
import inspect

import pytest

from chibchaweb.dominio import repositorios
from chibchaweb.servicio import dto, servicios

DTO = {
    "ResultadoAccesoDTO": ["registrado", "id_usuario", "nombre", "correo", "tipo_usuario", "rol", "operaciones",
                           "identificador_externo"],
    "DatosClienteDTO": ["telefono", "linea_residencia", "ciudad_residencia", "codigo_postal_residencia", "sitio",
                        "plataforma", "id_paquete", "id_plan", "linea_facturacion", "ciudad_facturacion",
                        "codigo_postal_facturacion", "numero_tarjeta", "vencimiento", "codigo_seguridad",
                        "franquicia", "codigo_distribuidor", "id_suscripcion", "identificador_externo", "nombre",
                        "correo"],
    "EmpleadoDTO": ["nombre", "documento", "correo", "telefono", "id_rol"],
    "DistribuidorDTO": ["nombre", "documento", "correo", "telefono"],
    "ResumenDTO": ["id", "titulo", "subtitulo", "estado"],
    "DetalleDTO": ["id", "titulo", "campos"],
    "ResultadoMigracionDTO": ["id_proceso", "validos", "invalidos", "entradas"],
}  # fmt: skip

# Atributos del modelo en el orden de la tabla (el __init__ los recibe en ese orden)
SERVICIOS = {
    "ServicioAcceso": ["proveedor", "validador", "usuarios", "catalogo", "suscripciones"],
    "ServicioClientes": ["validador", "usuarios", "catalogo", "suscripciones"],
    "ServicioEmpleados": ["usuarios", "catalogo"],
    "ServicioDistribuidores": ["usuarios"],
    "ServicioConsultas": ["usuarios", "tickets"],
    "ServicioFacturacion": ["pasarela", "suscripciones"],
    "ServicioDominios": ["constructor", "registrador", "solicitudes", "usuarios"],
    "ServicioComisiones": ["categorias", "comisiones", "usuarios", "suscripciones"],
    "ServicioSoporte": ["consultas", "usuarios", "tickets", "catalogo", "suscripciones"],
    "ServicioMigracion": ["fuente", "creadores", "migraciones", "usuarios", "suscripciones", "catalogo",
                          "unidad_trabajo"],
    "ServicioContingencia": ["gestor", "usuarios", "suscripciones", "comisiones", "solicitudes", "unidad_trabajo"],
}  # fmt: skip

METODOS = {
    "ServicioAcceso": [
        "iniciar_sesion",
        "registrarse",
        "consultar_paquetes",
        "consultar_planes",
        "verificar_usuario_activo",
    ],  # el último no es del modelo: P-25
    "ServicioClientes": ["modificar_perfil", "eliminar_perfil", "consultar_sitios"],
    "ServicioEmpleados": ["consultar_roles", "crear_empleado", "modificar_empleado", "eliminar_empleado"],
    "ServicioDistribuidores": ["crear_distribuidor", "modificar_distribuidor", "eliminar_distribuidor"],
    "ServicioConsultas": ["consultar_basico", "consultar_detalle"],
    "ServicioDominios": ["registrar_solicitud_dominio", "generar_y_enviar_solicitud_xml", "consultar_solicitudes"],
    "ServicioSoporte": [
        "registrar_ticket",
        "consultar_tickets_diario",
        "enrutar_por_nivel_servicio",
        "consultar_mis_tickets",
    ],
    "ServicioFacturacion": ["cargar_pago"],
    "ServicioComisiones": ["calcular_comision", "generar_cheque", "consultar_comisiones_sin_cheque"],  # P-08
    "ServicioMigracion": ["migrar_registros_legados", "confirmar_migracion", "cancelar_migracion"],
    "ServicioContingencia": [
        "sincronizar_respaldo",
        "cambiar_algoritmo_cifrado",
        "consultar_respaldo_pendiente",
    ],  # P-06
}


@pytest.mark.parametrize(("nombre", "campos"), DTO.items())
def test_dto_inmutables_con_los_campos_del_modelo(nombre, campos):
    clase = getattr(dto, nombre)
    assert dataclasses.is_dataclass(clase) and clase.__dataclass_params__.frozen
    assert sorted(f.name for f in dataclasses.fields(clase)) == sorted(campos)


def test_enumeraciones_con_los_literales_del_modelo():
    assert [e.name for e in dto.CategoriaPerfil] == ["PERSONAL", "PAQUETE_PLAN", "PAGO"]
    assert [e.name for e in dto.TipoEntidad] == ["CLIENTE", "EMPLEADO", "DISTRIBUIDOR", "TICKET"]
    assert servicios.CategoriaPerfil is dto.CategoriaPerfil and servicios.TipoEntidad is dto.TipoEntidad


def test_el_repr_de_los_datos_del_cliente_no_expone_la_tarjeta():
    datos = dto.DatosClienteDTO(numero_tarjeta="4242424242424242", codigo_seguridad="123", correo="a@b.co")
    assert "4242" not in repr(datos) and "123" not in repr(datos)


@pytest.mark.parametrize(("nombre", "parametros"), SERVICIOS.items())
def test_constructores_con_los_atributos_del_modelo(nombre, parametros):
    clase = getattr(servicios, nombre)
    assert list(inspect.signature(clase.__init__).parameters)[1:] == parametros


@pytest.mark.parametrize("nombre", SERVICIOS)
def test_los_servicios_no_reciben_mapeadores(nombre):
    anotaciones = inspect.get_annotations(getattr(servicios, nombre).__init__, eval_str=False).values()
    assert not any("Mapeador" in str(a) for a in anotaciones)
    assert hasattr(repositorios, "RepositorioUsuario")


@pytest.mark.parametrize(("nombre", "metodos"), METODOS.items())
def test_metodos_implementados(nombre, metodos):
    for metodo in metodos:
        assert callable(getattr(getattr(servicios, nombre), metodo))
