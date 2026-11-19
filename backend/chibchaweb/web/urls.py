"""Rutas de la API v1 (docs/api.md). Se agregan caso de uso por caso de uso."""

from django.urls import path

from chibchaweb.web import vistas

urlpatterns = [
    path("auth/oauth/inicio", vistas.VistaInicioOAuth.as_view()),
    path("auth/oauth/callback", vistas.VistaCallbackOAuth.as_view()),
    path("auth/sesion", vistas.VistaSesion.as_view()),
    path("auth/logout", vistas.VistaLogout.as_view()),
    path("auth/registro", vistas.VistaRegistro.as_view()),
    path("catalogo/paquetes", vistas.VistaPaquetes.as_view()),
    path("catalogo/planes", vistas.VistaPlanes.as_view()),
    path("catalogo/roles", vistas.VistaRoles.as_view()),
    path("clientes/me", vistas.VistaPerfil.as_view()),
    path("clientes/me/sitios", vistas.VistaSitios.as_view()),
    path("empleados", vistas.VistaEmpleados.as_view()),
    path("empleados/<int:id>", vistas.VistaEmpleado.as_view()),
    path("distribuidores", vistas.VistaDistribuidores.as_view()),
    path("distribuidores/<int:id>", vistas.VistaDistribuidor.as_view()),
    path("dominios/solicitudes", vistas.VistaSolicitudesDominio.as_view()),
    path("tickets", vistas.VistaTickets.as_view()),
    path("tickets/mios", vistas.VistaMisTickets.as_view()),
    path("tickets/diarios", vistas.VistaTicketsDiarios.as_view()),
    path("tickets/<int:id>", vistas.VistaTicket.as_view()),
    path("tickets/<int:id>/enrutamiento", vistas.VistaEnrutamiento.as_view()),
    path("migraciones", vistas.VistaMigraciones.as_view()),
    path("migraciones/<int:id>/confirmacion", vistas.VistaConfirmacionMigracion.as_view()),
    path("migraciones/<int:id>/cancelacion", vistas.VistaCancelacionMigracion.as_view()),
    path("contingencia/pendientes", vistas.VistaPendientesContingencia.as_view()),
    path("contingencia/algoritmo", vistas.VistaAlgoritmoContingencia.as_view()),
    path("contingencia/sincronizacion", vistas.VistaSincronizacionContingencia.as_view()),
    path("consultas/<str:tipo>", vistas.VistaConsultaBasica.as_view()),
    path("consultas/<str:tipo>/<int:id>", vistas.VistaConsultaDetalle.as_view()),
]
