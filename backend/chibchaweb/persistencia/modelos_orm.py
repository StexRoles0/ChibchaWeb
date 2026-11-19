"""Modelos ORM de ChibchaWEB (D-03): una clase por tabla de ``docs/schema.sql``, con ``managed = False``.

Solo los usan los mapeadores. No tienen lógica: describen las columnas para poder consultar con el ORM.
Las columnas ``TIMESTAMP`` (sin zona) guardan la hora en UTC; ``MarcaTemporal`` convierte de y hacia
datetimes con zona (el dominio trabaja en America/Bogota).
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from django.db import models

ZONA = ZoneInfo("America/Bogota")


class MarcaTemporal(models.DateTimeField):
    """``TIMESTAMP`` sin zona que guarda UTC; devuelve datetimes con zona America/Bogota."""

    def get_prep_value(self, value):
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None:
            return None
        if isinstance(value, datetime) and value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(ZONA)


def _fk(modelo, columna: str, *, null: bool = False, related_name: str = "+") -> models.ForeignKey:
    return models.ForeignKey(
        modelo, on_delete=models.DO_NOTHING, db_column=columna, null=null, blank=null, related_name=related_name
    )


def _uno_a_uno_pk(modelo, related_name: str) -> models.OneToOneField:
    """Subtipo (Class Table Inheritance): la llave primaria es a la vez la llave foránea del supertipo."""
    return models.OneToOneField(
        modelo, on_delete=models.DO_NOTHING, primary_key=True, db_column="id", related_name=related_name
    )


# --------------------------------------------------------------------------------------------------
# Catálogos
# --------------------------------------------------------------------------------------------------


class RolOrm(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=40)

    class Meta:
        managed = False
        db_table = "rol"


class RolOperacionOrm(models.Model):
    # La tabla tiene llave compuesta (id_rol, operacion); solo se lee, así que basta marcar una columna.
    operacion = models.CharField(max_length=60, primary_key=True)
    rol = _fk(RolOrm, "id_rol", related_name="operaciones")

    class Meta:
        managed = False
        db_table = "rol_operacion"


class FranquiciaOrm(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=20)
    patron_numero = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "franquicia"


class PaqueteHostingOrm(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=40)
    tarifa_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField(null=True)

    class Meta:
        managed = False
        db_table = "paquete_hosting"


class PlanPagoOrm(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=20)
    meses = models.SmallIntegerField()
    descuento = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        managed = False
        db_table = "plan_pago"


class NivelServicioOrm(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=40)
    orden = models.SmallIntegerField()
    es_ultimo = models.BooleanField()

    class Meta:
        managed = False
        db_table = "nivel_servicio"


# --------------------------------------------------------------------------------------------------
# Cuentas y perfiles
# --------------------------------------------------------------------------------------------------


class UsuarioOrm(models.Model):
    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=15)
    nombre = models.CharField(max_length=120)
    correo = models.CharField(max_length=120)
    telefono = models.CharField(max_length=20, null=True)
    activo = models.BooleanField()
    fecha_registro = MarcaTemporal()
    fecha_modificacion = MarcaTemporal()

    class Meta:
        managed = False
        db_table = "usuario"


class DistribuidorOrm(models.Model):
    usuario = _uno_a_uno_pk(UsuarioOrm, "distribuidor")
    documento = models.CharField(max_length=20)
    codigo = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = "distribuidor"


class EmpleadoOrm(models.Model):
    usuario = _uno_a_uno_pk(UsuarioOrm, "empleado")
    documento = models.CharField(max_length=20)
    rol = _fk(RolOrm, "id_rol")

    class Meta:
        managed = False
        db_table = "empleado"


class CuentaAccesoOrm(models.Model):
    id = models.AutoField(primary_key=True)
    titular = models.OneToOneField(
        UsuarioOrm, on_delete=models.DO_NOTHING, db_column="id_titular", related_name="cuenta"
    )
    identificador_externo = models.CharField(max_length=255)
    proveedor = models.CharField(max_length=50)
    fecha_vinculacion = MarcaTemporal()
    ultimo_acceso = MarcaTemporal(null=True)

    class Meta:
        managed = False
        db_table = "cuenta_acceso"


class DireccionOrm(models.Model):
    id = models.AutoField(primary_key=True)
    linea = models.CharField(max_length=150)
    ciudad = models.CharField(max_length=80)
    codigo_postal = models.CharField(max_length=10)
    pais = models.CharField(max_length=60)

    class Meta:
        managed = False
        db_table = "direccion"


class MedioPagoOrm(models.Model):
    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=15)

    class Meta:
        managed = False
        db_table = "medio_pago"


class TarjetaCreditoOrm(models.Model):
    # codigoSeguridad no tiene columna (RN-12): nunca se guarda.
    medio = _uno_a_uno_pk(MedioPagoOrm, "tarjeta")
    numero_cifrado = models.TextField()
    algoritmo_cifrado = models.CharField(max_length=20)
    ultimos_digitos = models.CharField(max_length=4)
    vencimiento = models.DateField()
    franquicia = _fk(FranquiciaOrm, "id_franquicia")

    class Meta:
        managed = False
        db_table = "tarjeta_credito"


class ClienteOrm(models.Model):
    usuario = _uno_a_uno_pk(UsuarioOrm, "cliente")
    residencia = _fk(DireccionOrm, "id_residencia")
    facturacion = _fk(DireccionOrm, "id_facturacion")
    medio_pago = _fk(MedioPagoOrm, "id_medio_pago")
    distribuidor = _fk(DistribuidorOrm, "id_distribuidor", null=True, related_name="referidos")

    class Meta:
        managed = False
        db_table = "cliente"


# --------------------------------------------------------------------------------------------------
# Hospedaje
# --------------------------------------------------------------------------------------------------


class SitioWebOrm(models.Model):
    id = models.AutoField(primary_key=True)
    subdominio = models.CharField(max_length=120)
    dominio_propio = models.CharField(max_length=255, null=True)
    plataforma = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = "sitio_web"


class SuscripcionOrm(models.Model):
    id = models.AutoField(primary_key=True)
    titular = _fk(ClienteOrm, "id_titular", related_name="suscripciones")
    sitio = models.OneToOneField(
        SitioWebOrm, on_delete=models.DO_NOTHING, db_column="id_sitio", related_name="suscripcion"
    )
    paquete = _fk(PaqueteHostingOrm, "id_paquete")
    plan = _fk(PlanPagoOrm, "id_plan")
    fecha_inicio = models.DateField()
    fecha_corte = models.DateField()
    activa = models.BooleanField()

    class Meta:
        managed = False
        db_table = "suscripcion"


# --------------------------------------------------------------------------------------------------
# Facturación y comisiones
# --------------------------------------------------------------------------------------------------


class ComisionOrm(models.Model):
    id = models.AutoField(primary_key=True)
    beneficiario = _fk(DistribuidorOrm, "id_beneficiario", related_name="comisiones")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    clientes_referidos = models.IntegerField()
    nombre_categoria = models.CharField(max_length=20)
    porcentaje = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        managed = False
        db_table = "comision"


class PagoOrm(models.Model):
    id = models.AutoField(primary_key=True)
    suscripcion = _fk(SuscripcionOrm, "id_suscripcion", related_name="pagos")
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = MarcaTemporal()
    estado = models.CharField(max_length=10)
    referencia_franquicia = models.CharField(max_length=100, null=True)
    comisionado = models.BooleanField()
    comision = _fk(ComisionOrm, "id_comision", null=True, related_name="pagos_base")

    class Meta:
        managed = False
        db_table = "pago"


class ChequeOrm(models.Model):
    id = models.AutoField(primary_key=True)
    comision = models.OneToOneField(
        ComisionOrm, on_delete=models.DO_NOTHING, db_column="id_comision", related_name="cheque"
    )
    numero = models.CharField(max_length=30)
    beneficiario = models.CharField(max_length=120)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_emision = models.DateField()

    class Meta:
        managed = False
        db_table = "cheque"


# --------------------------------------------------------------------------------------------------
# Dominios web y soporte
# --------------------------------------------------------------------------------------------------


class SolicitudDominioOrm(models.Model):
    id = models.AutoField(primary_key=True)
    solicitante = _fk(ClienteOrm, "id_solicitante", related_name="solicitudes")
    nombre = models.CharField(max_length=63)
    extension = models.CharField(max_length=20)
    fecha_solicitud = MarcaTemporal()
    fecha_envio = MarcaTemporal(null=True)
    estado = models.CharField(max_length=12)

    class Meta:
        managed = False
        db_table = "solicitud_dominio"


class TicketOrm(models.Model):
    id = models.AutoField(primary_key=True)
    reportante = _fk(UsuarioOrm, "id_reportante", related_name="tickets")
    sitio_afectado = _fk(SitioWebOrm, "id_sitio_afectado", null=True)
    nivel_actual = _fk(NivelServicioOrm, "id_nivel_actual")
    descripcion = models.TextField()
    fecha_creacion = MarcaTemporal()
    categoria = models.CharField(max_length=15)
    estado = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = "ticket"


class MovimientoTicketOrm(models.Model):
    id = models.AutoField(primary_key=True)
    ticket = _fk(TicketOrm, "id_ticket", related_name="movimientos")
    responsable = _fk(EmpleadoOrm, "id_responsable")
    nivel_resultante = _fk(NivelServicioOrm, "id_nivel_resultante")
    fecha = MarcaTemporal()
    observacion = models.TextField(null=True)
    estado_resultante = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = "movimiento_ticket"


# --------------------------------------------------------------------------------------------------
# Migración
# --------------------------------------------------------------------------------------------------


class ProcesoMigracionOrm(models.Model):
    id = models.AutoField(primary_key=True)
    ejecutor = _fk(EmpleadoOrm, "id_ejecutor")
    fecha_inicio = MarcaTemporal()
    fecha_fin = MarcaTemporal(null=True)
    estado = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = "proceso_migracion"


class EntradaLogOrm(models.Model):
    id = models.AutoField(primary_key=True)
    proceso = _fk(ProcesoMigracionOrm, "id_proceso", related_name="entradas")
    fecha = MarcaTemporal()
    nivel = models.CharField(max_length=12)
    mensaje = models.TextField()
    identificador_legado = models.CharField(max_length=50, null=True)
    tipo_registro = models.CharField(max_length=20, null=True)

    class Meta:
        managed = False
        db_table = "entrada_log"
