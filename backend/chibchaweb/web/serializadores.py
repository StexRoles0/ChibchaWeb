"""Serializadores: solo validan la forma (tipos, presencia) y crean los DTO. Las reglas son del dominio.

Los campos van en ``snake_case``: el parser ``camel-case`` ya convirtió el JSON de entrada.
"""

from __future__ import annotations

from rest_framework import serializers

from chibchaweb.servicio.dto import (
    CategoriaPerfil,
    CategoriaTicket,
    DatosClienteDTO,
    DistribuidorDTO,
    EmpleadoDTO,
    TipoEntidad,
)


class CallbackSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=2000)
    estado = serializers.CharField(max_length=500)


class InicioOAuthSerializer(serializers.Serializer):
    correo = serializers.CharField(required=False, allow_blank=False, max_length=254)


class InicioSimuladoSerializer(InicioOAuthSerializer):
    """Con ``SIMULAR_EXTERNOS`` el ``correo`` es obligatorio: arma el código ``dev:<correo>``."""

    correo = serializers.CharField(max_length=254)


class _CamposCliente(serializers.Serializer):
    """Campos de ``DatosClienteDTO`` que el cliente HTTP puede mandar (no ``identificadorExterno`` ni ``correo``)."""

    def crear_dto(self, **identidad) -> DatosClienteDTO:
        return DatosClienteDTO(**self.validated_data, **identidad)


def _texto(**opciones) -> serializers.CharField:
    return serializers.CharField(allow_blank=True, max_length=300, **opciones)


class RegistroSerializer(_CamposCliente):
    """Cuerpo de ``POST /auth/registro``: todos los datos, salvo los opcionales."""

    telefono = _texto()
    linea_residencia = _texto()
    ciudad_residencia = _texto()
    codigo_postal_residencia = _texto()
    sitio = _texto()
    plataforma = _texto()
    id_paquete = serializers.IntegerField()
    id_plan = serializers.IntegerField()
    linea_facturacion = _texto()
    ciudad_facturacion = _texto()
    codigo_postal_facturacion = _texto()
    numero_tarjeta = _texto()
    vencimiento = serializers.DateField()
    codigo_seguridad = _texto()
    franquicia = _texto()
    codigo_distribuidor = _texto(required=False)
    nombre = _texto(required=False)

    def crear_dto(self, pendiente: dict[str, str]) -> DatosClienteDTO:  # type: ignore[override]
        """Completa el DTO con la identidad verificada de la sesión (P-07); el nombre del cuerpo tiene prioridad."""
        datos = {**self.validated_data}
        datos["nombre"] = datos.get("nombre") or pendiente["nombre"]
        return DatosClienteDTO(
            **datos, identificador_externo=pendiente["identificador_externo"], correo=pendiente["correo"]
        )


class PerfilSerializer(_CamposCliente):
    """Cuerpo de ``PATCH /clientes/me``: parcial, solo el bloque de la pestaña activa."""

    nombre = _texto(required=False)
    telefono = _texto(required=False)
    linea_residencia = _texto(required=False)
    ciudad_residencia = _texto(required=False)
    codigo_postal_residencia = _texto(required=False)
    sitio = _texto(required=False)
    plataforma = _texto(required=False)
    id_paquete = serializers.IntegerField(required=False)
    id_plan = serializers.IntegerField(required=False)
    id_suscripcion = serializers.IntegerField(required=False)
    linea_facturacion = _texto(required=False)
    ciudad_facturacion = _texto(required=False)
    codigo_postal_facturacion = _texto(required=False)
    numero_tarjeta = _texto(required=False)
    vencimiento = serializers.DateField(required=False)
    codigo_seguridad = _texto(required=False)
    franquicia = _texto(required=False)


class CategoriaSerializer(serializers.Serializer):
    categoria = serializers.ChoiceField(choices=[c.value for c in CategoriaPerfil])

    def categoria_perfil(self) -> CategoriaPerfil:
        return CategoriaPerfil(self.validated_data["categoria"])


class ConsultaSerializer(serializers.Serializer):
    """``tipoEntidad`` (de la ruta) y ``filtro`` (de la query)."""

    tipo = serializers.ChoiceField(choices=[t.value for t in TipoEntidad])
    filtro = serializers.CharField(required=False, allow_blank=True, default="", max_length=200)

    def tipo_entidad(self) -> TipoEntidad:
        return TipoEntidad(self.validated_data["tipo"])


class DistribuidorSerializer(serializers.Serializer):
    """Cuerpo de ``POST|PUT /distribuidores``: solo la forma; el dominio valida formato y unicidad."""

    nombre = _texto()
    documento = _texto()
    correo = _texto()
    telefono = _texto()

    def crear_dto(self) -> DistribuidorDTO:
        return DistribuidorDTO(**self.validated_data)


class EmpleadoSerializer(DistribuidorSerializer):
    """Cuerpo de ``POST|PUT /empleados``."""

    id_rol = serializers.IntegerField()

    def crear_dto(self) -> EmpleadoDTO:  # type: ignore[override]
        return EmpleadoDTO(**self.validated_data)


def _clave_categoria(texto: str) -> str:
    """``"Base de datos"`` y ``"BASE_DATOS"`` son la misma categoría (el frontend manda el nombre legible)."""
    return texto.strip().upper().replace(" ", "_").replace("_DE_", "_")


class TicketSerializer(serializers.Serializer):
    """Cuerpo de ``POST /tickets``: ``{ categoria, descripcion, idSitio? }``."""

    categoria = serializers.CharField(max_length=40)
    descripcion = serializers.CharField(allow_blank=True, max_length=4100)
    id_sitio = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate_categoria(self, valor: str) -> str:
        clave = _clave_categoria(valor)
        if clave not in {c.value for c in CategoriaTicket}:
            raise serializers.ValidationError("Categoría de ticket inválida")
        return clave

    def categoria_ticket(self) -> CategoriaTicket:
        return CategoriaTicket(self.validated_data["categoria"])


class EnrutamientoSerializer(serializers.Serializer):
    """Cuerpo de ``POST /tickets/{id}/enrutamiento``. Sin observación el dominio responde 422."""

    escalar = serializers.BooleanField()
    observacion = serializers.CharField(required=False, allow_blank=True, default="", max_length=4100)


class FechaSerializer(serializers.Serializer):
    """``?fecha=AAAA-MM-DD`` de la bandeja diaria; sin fecha, hoy."""

    fecha = serializers.DateField(required=False)


class SolicitudDominioSerializer(serializers.Serializer):
    """Cuerpo de ``POST /dominios/solicitudes``: ``{ nombre, extension }`` (extensión con punto)."""

    nombre = _texto()
    extension = _texto()


class AlgoritmoSerializer(serializers.Serializer):
    """Cuerpo de ``PUT /contingencia/algoritmo``: ``{ nombre }``. El servicio decide si el algoritmo existe."""

    nombre = serializers.CharField(max_length=40)
