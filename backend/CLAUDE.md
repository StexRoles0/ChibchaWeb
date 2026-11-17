# Backend — Django 5 + DRF + PostgreSQL 16

Lee primero `../CLAUDE.md` y `../docs/arquitectura.md`. Lo que sigue complementa esos documentos, no los reemplaza.

## Estructura

```
backend/
├── config/
│   ├── settings.py          # lee .env (django-environ); REST_FRAMEWORK con camel-case
│   ├── urls.py              # /api/v1/ → chibchaweb.web.urls
│   └── contenedor.py        # composition root: ÚNICO lugar que importa todas las capas
├── chibchaweb/
│   ├── dominio/             # puro: sin django ni rest_framework
│   │   ├── errores.py       # ErrorDominio, ValidacionError(campo), ReglaNegocioError, EstadoInvalidoError,
│   │   │                    # NoEncontradoError, DuplicadoError(campo), ContingenciaActivaError
│   │   ├── cuentas.py       # Usuario, Cliente, Empleado, Distribuidor, CuentaAcceso, Rol, Direccion,
│   │   │                    # MedioPago, TarjetaCredito, Franquicia
│   │   ├── hospedaje.py     # PaqueteHosting, PlanPago, SitioWeb, Suscripcion, Plataforma
│   │   ├── facturacion.py   # Pago, Comision, Cheque, CategoriaDistribuidor(+Basica, Premium), EstadoPago
│   │   ├── dominios_web.py  # SolicitudDominio, ConstructorSolicitud, ConstructorXML, EstadoSolicitud
│   │   ├── soporte.py       # Ticket, MovimientoTicket, NivelServicio, CategoriaTicket, EstadoTicket
│   │   ├── migracion.py     # ProcesoMigracion, EntradaLog, RegistroLegado(+3), CreadorRegistroLegado(+3), …
│   │   ├── integraciones.py # ProveedorAutenticacion, IdentidadExterna, ValidadorMedioPago, PasarelaPago,
│   │   │                    # RegistradorDominio, FuenteLegada (ABC)
│   │   ├── respaldo.py      # GestorContingencia, AlgoritmoCifrado(+4), MedioRespaldo, ArchivoPlano
│   │   └── repositorios.py  # Repositorio* (ABC) + UnidadDeTrabajo
│   ├── servicio/
│   │   ├── dto.py           # @dataclass(frozen=True) de cada DTO + enums TipoEntidad, CategoriaPerfil
│   │   └── servicios.py     # los 11 Servicio*; reciben repositorios/adaptadores por __init__
│   ├── persistencia/
│   │   ├── modelos_orm.py   # models.Model con managed=False y db_table de schema.sql
│   │   ├── mapeadores.py    # Mapeador[T] (Generic, ABC) + 7 MapeadorX(Mapeador[X], RepositorioX)
│   │   └── transacciones.py # UnidadDeTrabajoDjango
│   ├── adaptadores/
│   │   ├── oauth.py, pagos.py, registrador.py, legado.py   # AdaptadorX reales
│   │   └── simulados.py     # implementaciones simuladas (decisiones D-06)
│   ├── web/
│   │   ├── urls.py, vistas.py, serializadores.py  # serializers solo validan forma y crean DTO
│   │   ├── permisos.py      # EsCliente, TieneOperacion("…")
│   │   ├── errores.py       # exception_handler: ErrorDominio → HTTP (api.md §Errores)
│   │   └── utilidades.py    # @transaccional, sesion_usuario(request)
│   └── tareas/management/commands/   # cargar_pagos, calcular_comisiones, generar_cheques
├── datos_legados/           # clientes.csv, hosting.csv, pagos.csv (fuente simulada)
└── tests/
    ├── falsos.py            # Repositorio*EnMemoria, adaptadores falsos
    ├── dominio/  servicio/  persistencia/  web/
    └── conftest.py          # aplica ../docs/schema.sql + seed_dev.sql en la BD de prueba
```

Si un archivo pasa de unas 600 líneas, se convierte en paquete (`dominio/cuentas/__init__.py`, que reexporta las clases). Así las rutas de import se mantienen.

## Cómo traducir el modelo a Python

```python
class Suscripcion:
    """Contrato de hospedaje de un sitio (DC-MDO-01)."""
    def __init__(self, titular: "Cliente", sitio: SitioWeb, paquete: PaqueteHosting, plan: PlanPago,
                 fecha_inicio: date, id: int | None = None, fecha_corte: date | None = None,
                 activa: bool = True, pagos: list["Pago"] | None = None):
        self._id = id
        ...
    @property
    def fecha_corte(self) -> date: return self._fecha_corte

    def monto_del_periodo(self) -> Decimal:          # montoDelPeriodo(): Decimal
        return self._paquete.calcular_monto(self._plan)

    def cobrar(self, pasarela: PasarelaPago) -> "Pago":   # cobrar(pasarela): Pago
        ...
```

- Las interfaces del modelo (`«interface»`) son `abc.ABC` con `@abstractmethod`. Las clases abstractas también, y solo sus métodos abstractos llevan `@abstractmethod`.
- Las colecciones `[0..*]` son listas privadas. Se exponen como `tuple` de solo lectura y se modifican únicamente con los métodos del modelo (`agregar_pago`, `agregar_referido`).
- Las fechas son `date`/`datetime` con zona `America/Bogota` (`USE_TZ=True`). Los montos son `Decimal`.
- Las validaciones lanzan las excepciones de `dominio.errores`. No devuelvas `False` para avisar un error, salvo en los métodos `validar(): Boolean` del modelo. Esos devuelven el booleano, pero el servicio lanza la excepción cuando el resultado es `False` y se requiere que sea válido.
- Los DTO son `@dataclass(frozen=True)` con los campos en `snake_case`. La capa web convierte a `camelCase` con el renderer.

## Vistas

```python
class VistaEnrutamiento(APIView):
    permission_classes = [TieneOperacion("ATENDER_TICKETS")]
    @transaccional
    def post(self, request, id):
        s = EnrutamientoSerializer(data=request.data); s.is_valid(raise_exception=True)
        contenedor().servicio_soporte.enrutar_por_nivel_servicio(
            id, sesion_usuario(request).id_usuario, s.validated_data["escalar"], s.validated_data["observacion"])
        return Response(status=204)
```

Una vista llama **un** método de servicio. La excepción es `POST /dominios/solicitudes`, que encadena DOM-01 y DOM-02 porque uno incluye al otro. Una vista no tiene `if` de negocio ni toca el ORM.

## Pruebas

- `tests/dominio/`: sin BD ni Django. Una prueba por regla, por ejemplo `test_rn01_monto_oro_semestral_es_54`.
- `tests/servicio/`: el servicio con `Repositorio*EnMemoria` y adaptadores falsos, para comprobar la orquestación.
- `tests/persistencia/`: `@pytest.mark.django_db` contra PostgreSQL. Se guarda y se vuelve a cargar cada agregado y se compara. Contingencia: se simula `OperationalError` y se verifica el archivo de respaldo.
- `tests/web/`: `APIClient` contra los endpoints, revisando los códigos de `api.md`.
- La cobertura mínima de `dominio` y `servicio` es del 85 %.

## Comandos

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q                         # todo
pytest tests/dominio -q           # rápido, sin BD
lint-imports                      # capas (.importlinter)
ruff check . && ruff format --check .
python manage.py runserver 0.0.0.0:8000
```

Dependencias base: `django>=5.0`, `djangorestframework`, `djangorestframework-camel-case`, `django-environ`, `psycopg[binary]`, `authlib`, `httpx`, `cryptography`, `twofish`. Desarrollo: `pytest`, `pytest-django`, `pytest-cov`, `import-linter`, `ruff`, `freezegun`.
