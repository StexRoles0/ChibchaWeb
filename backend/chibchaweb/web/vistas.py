"""Vistas de la API v1. Cada una llama un método de servicio; sin lógica de negocio ni ORM."""

from __future__ import annotations

from dataclasses import asdict

from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from chibchaweb.servicio.dto import DetalleDTO, ResumenDTO, TipoEntidad
from chibchaweb.web import serializadores as ser
from chibchaweb.web.autenticacion import AutenticacionSesion
from chibchaweb.web.permisos import (
    Autenticado,
    EsCliente,
    HayIdentidadPendiente,
    TieneOperacion,
    TieneOperacionDeConsulta,
)
from chibchaweb.web.utilidades import (
    a_diccionario,
    abrir_sesion,
    cerrar_sesion,
    consumir_estado,
    guardar_identidad_pendiente,
    identidad_pendiente,
    nuevo_estado,
    resultado_de_registro,
    resultado_de_sesion,
    sesion_usuario,
    transaccional,
    url_de_autorizacion,
    valor_de_campo,
)
from config.contenedor import contenedor


def _lista(resumenes: list[ResumenDTO]) -> Response:
    return Response([asdict(r) for r in resumenes])


def _detalle(detalle: DetalleDTO) -> Response:
    return Response({"id": detalle.id, "titulo": detalle.titulo, "campos": list(detalle.campos)})


class VistaBase(APIView):
    authentication_classes = [AutenticacionSesion]
    permission_classes = [AllowAny]


# --- Acceso --------------------------------------------------------------------------------------
class VistaInicioOAuth(VistaBase):
    """CU-AUTH-01: ``GET /auth/oauth/inicio[?correo=]``."""

    def get(self, request):
        modelo = ser.InicioSimuladoSerializer if settings.SIMULAR_EXTERNOS else ser.InicioOAuthSerializer
        s = modelo(data=request.query_params)
        s.is_valid(raise_exception=True)
        url = url_de_autorizacion(nuevo_estado(request), s.validated_data.get("correo"))
        return Response({"url": url})


class VistaCallbackOAuth(VistaBase):
    """CU-AUTH-02: ``POST /auth/oauth/callback``."""

    @transaccional
    def post(self, request):
        s = ser.CallbackSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        consumir_estado(request, s.validated_data["estado"])
        resultado = contenedor().servicio_acceso.iniciar_sesion(s.validated_data["codigo"])
        if resultado.registrado:
            abrir_sesion(request, resultado)
        else:
            guardar_identidad_pendiente(request, resultado)
        return Response(a_diccionario(resultado))


class VistaSesion(VistaBase):
    """``GET /auth/sesion``."""

    permission_classes = [Autenticado]

    def get(self, request):
        return Response(a_diccionario(resultado_de_sesion(sesion_usuario(request))))


class VistaLogout(VistaBase):
    """``POST /auth/logout``. También cancela el registro: acepta la sesión con identidad pendiente (AUTH-03)."""

    permission_classes = [Autenticado | HayIdentidadPendiente]

    def post(self, request):
        cerrar_sesion(request)
        return Response(status=204)


class VistaRegistro(VistaBase):
    """CU-AUTH-03: ``POST /auth/registro``."""

    permission_classes = [HayIdentidadPendiente]

    @transaccional
    def post(self, request):
        s = ser.RegistroSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        datos = s.crear_dto(identidad_pendiente(request))
        id_cliente = contenedor().servicio_acceso.registrarse(datos)
        resultado = resultado_de_registro(id_cliente, datos.nombre, datos.correo)
        abrir_sesion(request, resultado)
        return Response(a_diccionario(resultado), status=201)


class VistaPaquetes(VistaBase):
    """``GET /catalogo/paquetes``."""

    def get(self, request):
        return _lista(contenedor().servicio_acceso.consultar_paquetes())


class VistaPlanes(VistaBase):
    """``GET /catalogo/planes``."""

    def get(self, request):
        return _lista(contenedor().servicio_acceso.consultar_planes())


class VistaRoles(VistaBase):
    """``GET /catalogo/roles``."""

    permission_classes = [TieneOperacion("GESTIONAR_EMPLEADOS")]

    def get(self, request):
        return _lista(contenedor().servicio_empleados.consultar_roles())


# --- Clientes ------------------------------------------------------------------------------------
class VistaPerfil(VistaBase):
    """CU-CLI-01/02/03: ``GET|PATCH|DELETE /clientes/me``."""

    permission_classes = [EsCliente]

    def get(self, request):
        detalle = contenedor().servicio_consultas.consultar_detalle(
            TipoEntidad.CLIENTE, sesion_usuario(request).id_usuario
        )
        return _detalle(detalle)

    @transaccional
    def patch(self, request):
        categoria = ser.CategoriaSerializer(data=request.query_params)
        categoria.is_valid(raise_exception=True)
        cuerpo = ser.PerfilSerializer(data=request.data)
        cuerpo.is_valid(raise_exception=True)
        contenedor().servicio_clientes.modificar_perfil(
            sesion_usuario(request).id_usuario, categoria.categoria_perfil(), cuerpo.crear_dto()
        )
        return Response(status=204)

    @transaccional
    def delete(self, request):
        contenedor().servicio_clientes.eliminar_perfil(sesion_usuario(request).id_usuario)
        cerrar_sesion(request)
        return Response(status=204)


class VistaSitios(VistaBase):
    """``GET /clientes/me/sitios``."""

    permission_classes = [EsCliente]

    def get(self, request):
        return _lista(contenedor().servicio_clientes.consultar_sitios(sesion_usuario(request).id_usuario))


# --- Consultas -----------------------------------------------------------------------------------
class VistaConsultaBasica(VistaBase):
    """CU-CON-01: ``GET /consultas/{tipoEntidad}?filtro=``."""

    permission_classes = [TieneOperacionDeConsulta]

    def get(self, request, tipo):
        s = ser.ConsultaSerializer(data={"tipo": tipo, "filtro": request.query_params.get("filtro", "")})
        s.is_valid(raise_exception=True)
        return _lista(contenedor().servicio_consultas.consultar_basico(s.tipo_entidad(), s.validated_data["filtro"]))


class VistaConsultaDetalle(VistaBase):
    """CU-CON-02: ``GET /consultas/{tipoEntidad}/{id}``."""

    permission_classes = [TieneOperacionDeConsulta]

    def get(self, request, tipo, id):
        s = ser.ConsultaSerializer(data={"tipo": tipo})
        s.is_valid(raise_exception=True)
        return _detalle(contenedor().servicio_consultas.consultar_detalle(s.tipo_entidad(), id))


# --- Empleados -----------------------------------------------------------------------------------
class VistaEmpleados(VistaBase):
    """CU-EMP-01/02: ``GET|POST /empleados``."""

    permission_classes = [TieneOperacion("GESTIONAR_EMPLEADOS")]

    def get(self, request):
        s = ser.ConsultaSerializer(data={"tipo": "EMPLEADO", "filtro": request.query_params.get("filtro", "")})
        s.is_valid(raise_exception=True)
        return _lista(
            contenedor().servicio_consultas.consultar_basico(TipoEntidad.EMPLEADO, s.validated_data["filtro"])
        )

    @transaccional
    def post(self, request):
        s = ser.EmpleadoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response({"id": contenedor().servicio_empleados.crear_empleado(s.crear_dto())}, status=201)


class VistaEmpleado(VistaBase):
    """CU-EMP-01/03/04: ``GET|PUT|DELETE /empleados/{id}``."""

    permission_classes = [TieneOperacion("GESTIONAR_EMPLEADOS")]

    def get(self, request, id):
        return _detalle(contenedor().servicio_consultas.consultar_detalle(TipoEntidad.EMPLEADO, id))

    @transaccional
    def put(self, request, id):
        s = ser.EmpleadoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        contenedor().servicio_empleados.modificar_empleado(id, s.crear_dto())
        return Response(status=204)

    @transaccional
    def delete(self, request, id):
        contenedor().servicio_empleados.eliminar_empleado(id)
        return Response(status=204)


# --- Distribuidores ------------------------------------------------------------------------------
class VistaDistribuidores(VistaBase):
    """CU-DIS-01/02: ``GET|POST /distribuidores``."""

    permission_classes = [TieneOperacion("GESTIONAR_DISTRIBUIDORES")]

    def get(self, request):
        s = ser.ConsultaSerializer(data={"tipo": "DISTRIBUIDOR", "filtro": request.query_params.get("filtro", "")})
        s.is_valid(raise_exception=True)
        return _lista(
            contenedor().servicio_consultas.consultar_basico(TipoEntidad.DISTRIBUIDOR, s.validated_data["filtro"])
        )

    @transaccional
    def post(self, request):
        """Devuelve ``{ id, codigo }``: el código generado se lee del detalle recién creado (P-26)."""
        s = ser.DistribuidorSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        id_nuevo = contenedor().servicio_distribuidores.crear_distribuidor(s.crear_dto())
        detalle = contenedor().servicio_consultas.consultar_detalle(TipoEntidad.DISTRIBUIDOR, id_nuevo)
        return Response({"id": id_nuevo, "codigo": valor_de_campo(detalle, "codigo")}, status=201)


class VistaDistribuidor(VistaBase):
    """CU-DIS-01/03/04: ``GET|PUT|DELETE /distribuidores/{id}``."""

    permission_classes = [TieneOperacion("GESTIONAR_DISTRIBUIDORES")]

    def get(self, request, id):
        return _detalle(contenedor().servicio_consultas.consultar_detalle(TipoEntidad.DISTRIBUIDOR, id))

    @transaccional
    def put(self, request, id):
        s = ser.DistribuidorSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        contenedor().servicio_distribuidores.modificar_distribuidor(id, s.crear_dto())
        return Response(status=204)

    @transaccional
    def delete(self, request, id):
        contenedor().servicio_distribuidores.eliminar_distribuidor(id)
        return Response(status=204)


# --- Dominios ------------------------------------------------------------------------------------
class VistaSolicitudesDominio(VistaBase):
    """CU-DOM-01/02: ``POST|GET /dominios/solicitudes``."""

    permission_classes = [EsCliente]

    def get(self, request):
        return _lista(contenedor().servicio_dominios.consultar_solicitudes(sesion_usuario(request).id_usuario))

    @transaccional
    def post(self, request):
        """Único caso con dos llamadas: DOM-01 incluye a DOM-02 (api.md). Un registrador caído responde 201 FALLIDA."""
        s = ser.SolicitudDominioSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        servicio = contenedor().servicio_dominios
        id_solicitud = servicio.registrar_solicitud_dominio(
            sesion_usuario(request).id_usuario, s.validated_data["nombre"], s.validated_data["extension"]
        )
        estado = servicio.generar_y_enviar_solicitud_xml(id_solicitud)
        return Response({"id": id_solicitud, "estado": estado.value}, status=201)


# --- Soporte -------------------------------------------------------------------------------------
class VistaTickets(VistaBase):
    """CU-SOP-01: ``POST /tickets``."""

    permission_classes = [Autenticado]

    @transaccional
    def post(self, request):
        s = ser.TicketSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        id_ticket = contenedor().servicio_soporte.registrar_ticket(
            sesion_usuario(request).id_usuario,
            s.categoria_ticket(),
            s.validated_data["descripcion"],
            s.validated_data["id_sitio"],
        )
        return Response({"id": id_ticket}, status=201)


class VistaMisTickets(VistaBase):
    """``GET /tickets/mios``."""

    permission_classes = [Autenticado]

    def get(self, request):
        return _lista(contenedor().servicio_soporte.consultar_mis_tickets(sesion_usuario(request).id_usuario))


class VistaTicketsDiarios(VistaBase):
    """CU-SOP-02: ``GET /tickets/diarios?fecha=``."""

    permission_classes = [TieneOperacion("ATENDER_TICKETS")]

    def get(self, request):
        s = ser.FechaSerializer(data=request.query_params)
        s.is_valid(raise_exception=True)
        fecha = s.validated_data.get("fecha") or timezone.localdate()
        return _lista(contenedor().servicio_soporte.consultar_tickets_diario(fecha))


class VistaTicket(VistaBase):
    """``GET /tickets/{id}``."""

    permission_classes = [TieneOperacion("ATENDER_TICKETS")]

    def get(self, request, id):
        return _detalle(contenedor().servicio_consultas.consultar_detalle(TipoEntidad.TICKET, id))


class VistaEnrutamiento(VistaBase):
    """CU-SOP-03: ``POST /tickets/{id}/enrutamiento``."""

    permission_classes = [TieneOperacion("ATENDER_TICKETS")]

    @transaccional
    def post(self, request, id):
        s = ser.EnrutamientoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        contenedor().servicio_soporte.enrutar_por_nivel_servicio(
            id, sesion_usuario(request).id_usuario, s.validated_data["escalar"], s.validated_data["observacion"]
        )
        return Response(status=204)


# --- Migración -----------------------------------------------------------------------------------
class VistaMigraciones(VistaBase):
    """CU-MIG-01 fase 1: ``POST /migraciones`` (simulación)."""

    permission_classes = [TieneOperacion("MIGRAR_DATOS")]

    @transaccional
    def post(self, request):
        resultado = contenedor().servicio_migracion.migrar_registros_legados(sesion_usuario(request).id_usuario)
        return Response(asdict(resultado), status=201)


class VistaConfirmacionMigracion(VistaBase):
    """CU-MIG-01 fase 2: ``POST /migraciones/{id}/confirmacion`` -> ``EJECUTADA`` o ``REVERTIDA``."""

    permission_classes = [TieneOperacion("MIGRAR_DATOS")]

    @transaccional
    def post(self, request, id):
        estado = contenedor().servicio_migracion.confirmar_migracion(id)
        return Response({"estado": estado.value})


class VistaCancelacionMigracion(VistaBase):
    """CU-MIG-01: ``POST /migraciones/{id}/cancelacion`` -> ``CANCELADA``."""

    permission_classes = [TieneOperacion("MIGRAR_DATOS")]

    @transaccional
    def post(self, request, id):
        contenedor().servicio_migracion.cancelar_migracion(id)
        return Response({"estado": "CANCELADA"})


# --- Contingencia (RT04) -------------------------------------------------------------------------
class VistaPendientesContingencia(VistaBase):
    """``GET /contingencia/pendientes``."""

    permission_classes = [TieneOperacion("GESTIONAR_CONTINGENCIA")]

    def get(self, request):
        return _lista(contenedor().servicio_contingencia.consultar_respaldo_pendiente())


class VistaAlgoritmoContingencia(VistaBase):
    """``PUT /contingencia/algoritmo``."""

    permission_classes = [TieneOperacion("GESTIONAR_CONTINGENCIA")]

    def put(self, request):
        s = ser.AlgoritmoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        contenedor().servicio_contingencia.cambiar_algoritmo_cifrado(s.validated_data["nombre"])
        return Response(status=204)


class VistaSincronizacionContingencia(VistaBase):
    """``POST /contingencia/sincronizacion``. Sin ``@transaccional``: el servicio abre su propia unidad de trabajo."""

    permission_classes = [TieneOperacion("GESTIONAR_CONTINGENCIA")]

    def post(self, request):
        return Response({"sincronizados": contenedor().servicio_contingencia.sincronizar_respaldo()})
