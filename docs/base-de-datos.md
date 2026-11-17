# Base de datos

- **Motor:** PostgreSQL 16. El DDL completo (24 tablas, 7 índices y los catálogos) está en `docs/schema.sql`, que es el modelo ER-PER-01 del documento. Los datos de desarrollo están en `docs/seed_dev.sql`.
- **Docker:** los dos archivos se montan en `/docker-entrypoint-initdb.d/` como `01_schema.sql` y `02_seed.sql`.
- **Django no crea ni migra el esquema.** Los modelos ORM de `chibchaweb/persistencia/modelos_orm.py` llevan `managed = False` y `db_table` explícito, y solo los usan los mapeadores. En las pruebas, un fixture de sesión (`conftest.py`) aplica `schema.sql` + `seed_dev.sql` a la BD de pruebas (`--no-migrations`).

## Patrones de mapeo (de DC-PER-01)

| Patrón | Dónde |
|---|---|
| Identity Field | `id SERIAL` en cada tabla raíz y `_id` en el objeto del dominio |
| Class Table Inheritance | `usuario` → `cliente` / `empleado` / `distribuidor` (discriminador `usuario.tipo`); `medio_pago` → `tarjeta_credito` (`medio_pago.tipo = 'TARJETA'`) |
| Foreign Key Mapping | 1:N con FK en el hijo; 1:1 de composición con FK `UNIQUE` (`cliente.id_residencia`, `suscripcion.id_sitio`, `cheque.id_comision`, `cuenta_acceso.id_titular`) |
| Dependent Mapping | `Rol.operaciones` → `rol_operacion` (lo lee `MapeadorCatalogo.buscarRol`) |
| Enumeraciones | `VARCHAR` + `CHECK` con los literales exactos |
| Bajas | lógicas (`usuario.activo`, `suscripcion.activa`), sin `ON DELETE CASCADE` |

## Qué tablas toca cada mapeador

| Mapeador (implementa) | Agregado | Tablas |
|---|---|---|
| `MapeadorUsuario` (`RepositorioUsuario`) | Usuario y subtipos, CuentaAcceso, Direccion, MedioPago/TarjetaCredito | usuario, cliente, empleado, distribuidor, cuenta_acceso, direccion, medio_pago, tarjeta_credito |
| `MapeadorSuscripcion` (`RepositorioSuscripcion`) | Suscripcion, SitioWeb, Pago | suscripcion, sitio_web, pago |
| `MapeadorComision` (`RepositorioComision`) | Comision, Cheque (marca `pago.id_comision`) | comision, cheque, pago (solo actualiza) |
| `MapeadorSolicitudDominio` (`RepositorioSolicitudDominio`) | SolicitudDominio | solicitud_dominio |
| `MapeadorTicket` (`RepositorioTicket`) | Ticket, MovimientoTicket | ticket, movimiento_ticket |
| `MapeadorMigracion` (`RepositorioMigracion`) | ProcesoMigracion, EntradaLog | proceso_migracion, entrada_log |
| `MapeadorCatalogo` (`RepositorioCatalogo`) | catálogos (solo lectura) | paquete_hosting, plan_pago, franquicia, rol, rol_operacion, nivel_servicio |

Para cargar un agregado no se hacen consultas N+1: se usan `select_related`/`prefetch_related` sobre los modelos ORM o SQL con `JOIN`. Las referencias a **otros agregados** (por ejemplo `Ticket.reportante`) se cargan por id con el repositorio que les corresponde, o como un objeto reducido, según diga el mapeador. No se cargan grafos completos.

## Tarjeta

`tarjeta_credito.numero_cifrado` guarda `base64(cifrado)` hecho con el algoritmo activo del `GestorContingencia`; `algoritmo_cifrado` guarda su nombre; `ultimos_digitos` los 4 últimos. Para leer, el mapeador descifra con el algoritmo que dice la fila. La clave sale de `settings.CLAVE_CIFRADO` (variable de entorno, 32 bytes en base64).
