# Capa de servicio

Servicios (uno por módulo de casos de uso) y DTO. Los servicios dependen solo del dominio (clases, interfaces de integración y de repositorio). **Nunca importan mapeadores ni modelos ORM.**

> Convenciones: visibilidad `-` privada, `+` pública, `#` protegida. La multiplicidad acompaña al tipo (`[0..*]`, `[1..*]`, `[0..1]`). Getters/setters no se listan: existe uno por atributo privado salvo en colecciones, que se manipulan solo con los métodos listados. Las subclases listan solo lo propio y lo que sobrescriben. En Python los nombres se traducen a `snake_case` de forma mecánica (`validarDatosFacturacion` → `validar_datos_facturacion`); las clases conservan su nombre.

## Capa de servicio — Servicios

### `ServicioAcceso`
Módulo Python: `chibchaweb.servicio.servicios`

Servicio de los casos de uso del módulo AUTH: inicio de sesión con el proveedor externo y autoregistro de clientes.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `proveedor` | `-` | `ProveedorAutenticacion` | Adaptador del proveedor de autenticación (inyectado). | Referencia obligatoria |
| `validador` | `-` | `ValidadorMedioPago` | Adaptador de verificación de medios de pago (inyectado). | Referencia obligatoria |
| `usuarios` | `-` | `RepositorioUsuario` | Repositorio del agregado Usuario (inyectado). | Referencia obligatoria |
| `catalogo` | `-` | `RepositorioCatalogo` | Repositorio de catálogos (inyectado). | Referencia obligatoria |
| `suscripciones` | `-` | `RepositorioSuscripcion` | Repositorio del agregado Suscripcion (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `iniciarSesion` | `+` | `codigoAutorizacion: String` | `ResultadoAccesoDTO` | CU-AUTH-02. Autoriza con el proveedor, busca al usuario por identificador externo o, si el correo está verificado, por correo para vincularlo; si no existe devuelve los datos para el registro. |
| `registrarse` | `+` | `datos: DatosClienteDTO` | `Integer` | CU-AUTH-03. Crea el cliente con direcciones, tarjeta, sitio y suscripción; valida los datos de facturación, asocia el distribuidor si el código es válido y vincula la cuenta. |
| `consultarPaquetes` | `+` | `—` | `ResumenDTO [0..*]` | Lista los paquetes con su tarifa para el paso 2 del registro. |
| `consultarPlanes` | `+` | `—` | `ResumenDTO [0..*]` | Lista los planes con su descuento para el paso 2 del registro. |

### `ServicioClientes`
Módulo Python: `chibchaweb.servicio.servicios`

Servicio de la autogestión del perfil del cliente (módulo CLI).

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `validador` | `-` | `ValidadorMedioPago` | Adaptador de verificación de medios de pago (inyectado). | Referencia obligatoria |
| `usuarios` | `-` | `RepositorioUsuario` | Repositorio del agregado Usuario (inyectado). | Referencia obligatoria |
| `catalogo` | `-` | `RepositorioCatalogo` | Repositorio de catálogos (inyectado). | Referencia obligatoria |
| `suscripciones` | `-` | `RepositorioSuscripcion` | Repositorio del agregado Suscripcion (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `modificarPerfil` | `+` | `idCliente: Integer, categoria: CategoriaPerfil, datos: DatosClienteDTO` | `void` | CU-CLI-03. Aplica el bloque indicado por categoria; revalida dirección y tarjeta si cambian. |
| `eliminarPerfil` | `+` | `idCliente: Integer` | `void` | CU-CLI-02. Inactiva al cliente y suspende sus suscripciones. |
| `consultarSitios` | `+` | `idCliente: Integer` | `ResumenDTO [0..*]` | Lista los sitios del cliente (para el selector de sitio afectado en M-10). **(agregado en implementación)** |

### `ServicioEmpleados`
Módulo Python: `chibchaweb.servicio.servicios`

Servicio de la administración de empleados (módulo EMP).

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `usuarios` | `-` | `RepositorioUsuario` | Repositorio del agregado Usuario (inyectado). | Referencia obligatoria |
| `catalogo` | `-` | `RepositorioCatalogo` | Repositorio de catálogos (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `crearEmpleado` | `+` | `datos: EmpleadoDTO` | `Integer` | CU-EMP-02. Registra un empleado con su rol. |
| `modificarEmpleado` | `+` | `idEmpleado: Integer, datos: EmpleadoDTO` | `void` | CU-EMP-03. Actualiza los datos del empleado. |
| `eliminarEmpleado` | `+` | `idEmpleado: Integer` | `void` | CU-EMP-04. Inactiva al empleado. |
| `consultarRoles` | `+` | `—` | `ResumenDTO [0..*]` | Lista los cargos para el formulario. |

### `ServicioDistribuidores`
Módulo Python: `chibchaweb.servicio.servicios`

Servicio de la administración de distribuidores (módulo DIS).

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `usuarios` | `-` | `RepositorioUsuario` | Repositorio del agregado Usuario (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `crearDistribuidor` | `+` | `datos: DistribuidorDTO` | `Integer` | CU-DIS-02. Registra un distribuidor y genera su código. |
| `modificarDistribuidor` | `+` | `idDistribuidor: Integer, datos: DistribuidorDTO` | `void` | CU-DIS-03. Actualiza los datos del distribuidor. |
| `eliminarDistribuidor` | `+` | `idDistribuidor: Integer` | `void` | CU-DIS-04. Inactiva al distribuidor. |

### `ServicioConsultas`
Módulo Python: `chibchaweb.servicio.servicios`

Servicio de las consultas básica y detallada parametrizadas por tipo de entidad (módulo CON).

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `usuarios` | `-` | `RepositorioUsuario` | Repositorio del agregado Usuario (inyectado). | Referencia obligatoria |
| `tickets` | `-` | `RepositorioTicket` | Repositorio del agregado Ticket (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `consultarBasico` | `+` | `tipoEntidad: TipoEntidad, filtro: String` | `ResumenDTO [0..*]` | CU-CON-01. Devuelve el listado resumido de la entidad indicada. |
| `consultarDetalle` | `+` | `tipoEntidad: TipoEntidad, id: Integer` | `DetalleDTO` | CU-CON-02. Devuelve la vista ampliada del registro. |

### `ServicioFacturacion`
Módulo Python: `chibchaweb.servicio.servicios`

Servicio del cobro automático periódico (módulo FAC). Lo dispara el programador de tareas.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `pasarela` | `-` | `PasarelaPago` | Adaptador del procesador de pagos (inyectado). | Referencia obligatoria |
| `suscripciones` | `-` | `RepositorioSuscripcion` | Repositorio del agregado Suscripcion (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `cargarPago` | `+` | `fechaCorte: Date` | `Integer` | CU-FAC-01. Cobra las suscripciones vencidas a la fecha de corte y devuelve cuántos cobros procesó. |

### `ServicioDominios`
Módulo Python: `chibchaweb.servicio.servicios`

Servicio del registro y envío de solicitudes de dominio (módulo DOM).

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `constructor` | `-` | `ConstructorSolicitud` | Constructor del documento de solicitud (inyectado). | Referencia obligatoria |
| `registrador` | `-` | `RegistradorDominio` | Adaptador del registrador de dominios (inyectado). | Referencia obligatoria |
| `solicitudes` | `-` | `RepositorioSolicitudDominio` | Repositorio de solicitudes de dominio (inyectado). | Referencia obligatoria |
| `usuarios` | `-` | `RepositorioUsuario` | Repositorio del agregado Usuario (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `registrarSolicitudDominio` | `+` | `idCliente: Integer, nombre: String, extension: String` | `Integer` | CU-DOM-01. Crea y valida la solicitud del cliente. |
| `generarYEnviarSolicitudXML` | `+` | `idSolicitud: Integer` | `EstadoSolicitud` | CU-DOM-02. Construye el XML con el Builder, lo envía y persiste el estado. |
| `consultarSolicitudes` | `+` | `idCliente: Integer` | `ResumenDTO [0..*]` | Lista las solicitudes del cliente. |

### `ServicioComisiones`
Módulo Python: `chibchaweb.servicio.servicios`

Servicio de la liquidación de comisiones y emisión de cheques (módulo COM). Lo dispara el programador de tareas.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `categorias` | `-` | `CategoriaDistribuidor [1..*]` | Estrategias de categoría de distribuidor (inyectadas). | Al menos una |
| `comisiones` | `-` | `RepositorioComision` | Repositorio del agregado Comision (inyectado). | Referencia obligatoria |
| `usuarios` | `-` | `RepositorioUsuario` | Repositorio del agregado Usuario (inyectado). | Referencia obligatoria |
| `suscripciones` | `-` | `RepositorioSuscripcion` | Repositorio del agregado Suscripcion (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `calcularComision` | `+` | `fechaInicio: Date, fechaFin: Date` | `Integer` | CU-COM-01. Liquida las comisiones del periodo para cada distribuidor y devuelve cuántas creó. |
| `generarCheque` | `+` | `idComision: Integer` | `void` | CU-COM-02. Emite el cheque de una comisión. |
| `consultarComisionesSinCheque` | `+` | `—` | `ResumenDTO [0..*]` | Lista las comisiones que aún no tienen cheque (tarea generar_cheques). **(agregado en implementación)** |

### `ServicioSoporte`
Módulo Python: `chibchaweb.servicio.servicios`

Servicio del registro, consulta y enrutamiento de tickets (módulo SOP).

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `consultas` | `-` | `ServicioConsultas` | Servicio de consultas reutilizado (include de SOP-02 hacia CON). | Referencia obligatoria |
| `usuarios` | `-` | `RepositorioUsuario` | Repositorio del agregado Usuario (inyectado). | Referencia obligatoria |
| `tickets` | `-` | `RepositorioTicket` | Repositorio del agregado Ticket (inyectado). | Referencia obligatoria |
| `catalogo` | `-` | `RepositorioCatalogo` | Repositorio de catálogos (inyectado). | Referencia obligatoria |
| `suscripciones` | `-` | `RepositorioSuscripcion` | Repositorio del agregado Suscripcion (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `registrarTicket` | `+` | `idUsuario: Integer, categoria: CategoriaTicket, descripcion: String, idSitio: Integer [0..1]` | `Integer` | CU-SOP-01. Crea el ticket en el nivel de servicio inicial. |
| `consultarTicketsDiario` | `+` | `fecha: Date` | `ResumenDTO [0..*]` | CU-SOP-02. Lista los tickets creados en la fecha y los abiertos. |
| `enrutarPorNivelServicio` | `+` | `idTicket: Integer, idEmpleado: Integer, escalar: Boolean, observacion: String` | `void` | CU-SOP-03. Resuelve el ticket o lo escala al siguiente nivel. |
| `consultarMisTickets` | `+` | `idUsuario: Integer` | `ResumenDTO [0..*]` | Lista los tickets del usuario. |

### `ServicioMigracion`
Módulo Python: `chibchaweb.servicio.servicios`

Servicio de la migración de datos legados en dos fases (módulo MIG). Abre la transacción de la ejecución real.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `fuente` | `-` | `FuenteLegada` | Adaptador del sistema legado (inyectado). | Referencia obligatoria |
| `creadores` | `-` | `CreadorRegistroLegado [1..*]` | Creadores de registros legados, uno por tipo (inyectados). | Al menos uno |
| `migraciones` | `-` | `RepositorioMigracion` | Repositorio del agregado ProcesoMigracion (inyectado). | Referencia obligatoria |
| `usuarios` | `-` | `RepositorioUsuario` | Repositorio del agregado Usuario (inyectado). | Referencia obligatoria |
| `suscripciones` | `-` | `RepositorioSuscripcion` | Repositorio del agregado Suscripcion (inyectado). | Referencia obligatoria |
| `catalogo` | `-` | `RepositorioCatalogo` | Repositorio de catálogos (inyectado). | Referencia obligatoria |
| `unidadTrabajo` | `-` | `UnidadDeTrabajo` | Unidad de trabajo para la transacción de la migración real (inyectada). **(agregado en implementación)** | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `migrarRegistrosLegados` | `+` | `idEjecutor: Integer` | `ResultadoMigracionDTO` | CU-MIG-01 (fase 1). Ejecuta la simulación y devuelve el log. |
| `confirmarMigracion` | `+` | `idProceso: Integer` | `EstadoMigracion` | CU-MIG-01 (fase 2). Aprueba, prepara y escribe en una transacción; revierte si falla. |
| `cancelarMigracion` | `+` | `idProceso: Integer` | `void` | CU-MIG-01. Cancela el proceso. |

### `ServicioContingencia`
Módulo Python: `chibchaweb.servicio.servicios`

Servicio técnico de RT04: sincroniza el respaldo cifrado con la base de datos y cambia el algoritmo de cifrado en tiempo de ejecución.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `gestor` | `-` | `GestorContingencia` | Gestor de contingencia compartido (inyectado). | Referencia obligatoria |
| `usuarios` | `-` | `RepositorioUsuario` | Repositorio del agregado Usuario (inyectado). | Referencia obligatoria |
| `suscripciones` | `-` | `RepositorioSuscripcion` | Repositorio del agregado Suscripcion (inyectado). | Referencia obligatoria |
| `comisiones` | `-` | `RepositorioComision` | Repositorio del agregado Comision (inyectado). | Referencia obligatoria |
| `solicitudes` | `-` | `RepositorioSolicitudDominio` | Repositorio de solicitudes de dominio (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `sincronizarRespaldo` | `+` | `—` | `Integer` | Reinserta los eventos pendientes con el mapeador que corresponde y confirma la sincronización. |
| `cambiarAlgoritmoCifrado` | `+` | `nombre: String` | `void` | Cambia el algoritmo de cifrado activo (RT04). |
| `consultarRespaldoPendiente` | `+` | `—` | `ResumenDTO [0..*]` | Lista los eventos pendientes del respaldo (pantalla M-20). **(agregado en implementación)** |

### `CategoriaPerfil` — «enumeration»
Módulo Python: `chibchaweb.servicio.servicios`

Enumeración del bloque de datos que se modifica en una operación de modificación de perfil.

| Literal | Descripción |
|---|---|
| `PERSONAL` | Información personal y del sitio. |
| `PAQUETE_PLAN` | Paquete y plan de una suscripción. |
| `PAGO` | Dirección de facturación y tarjeta. |

### `TipoEntidad` — «enumeration»
Módulo Python: `chibchaweb.servicio.servicios`

Enumeración del tipo de entidad que reciben las consultas parametrizadas.

| Literal | Descripción |
|---|---|
| `CLIENTE` | Consulta de clientes. |
| `EMPLEADO` | Consulta de empleados. |
| `DISTRIBUIDOR` | Consulta de distribuidores. |
| `TICKET` | Consulta de tickets. |

## Capa de servicio — Objetos de transferencia

### `ResultadoAccesoDTO` — «DTO»
Módulo Python: `chibchaweb.servicio.dto`

Objeto de transferencia con el resultado de un inicio de sesión: identifica al usuario registrado o devuelve los datos para prellenar el registro.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `registrado` | `-` | `Boolean` | Indica si la identidad corresponde a un usuario registrado. | true / false |
| `idUsuario` | `-` | `Integer [0..1]` | Identificador del usuario autenticado. | Entero o nulo si no está registrado |
| `nombre` | `-` | `String` | Nombre del usuario o nombre verificado para prellenar. | Cadena |
| `correo` | `-` | `String` | Correo del usuario o correo verificado para prellenar. | Correo |
| `tipoUsuario` | `-` | `String` | Tipo de usuario. | CLIENTE, EMPLEADO |
| `rol` | `-` | `String [0..1]` | Cargo del empleado. | Nombre de rol o nulo |
| `operaciones` | `-` | `String [0..*]` | Operaciones permitidas para armar el menú. | Cero o más |
| `identificadorExterno` | `-` | `String [0..1]` | sub del proveedor cuando registrado = false; la vista lo guarda en sesión y no lo serializa. **(agregado en implementación, P-07)** | Nulo si registrado = true |

### `DatosClienteDTO` — «DTO»
Módulo Python: `chibchaweb.servicio.dto`

Objeto de transferencia con los datos del formulario de registro y de modificación de perfil del cliente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `telefono` | `-` | `String` | Teléfono. | Cadena |
| `lineaResidencia` | `-` | `String` | Línea de la dirección de residencia. | Cadena |
| `ciudadResidencia` | `-` | `String` | Ciudad de residencia. | Cadena |
| `codigoPostalResidencia` | `-` | `String` | Código postal de residencia. | Cadena |
| `sitio` | `-` | `String` | Nombre del sitio a hospedar. | Cadena |
| `plataforma` | `-` | `String` | Plataforma elegida. | WINDOWS o UNIX |
| `idPaquete` | `-` | `Integer` | Paquete elegido. | Id de PaqueteHosting |
| `idPlan` | `-` | `Integer` | Plan elegido. | Id de PlanPago |
| `lineaFacturacion` | `-` | `String` | Línea de la dirección de facturación. | Cadena |
| `ciudadFacturacion` | `-` | `String` | Ciudad de facturación. | Cadena |
| `codigoPostalFacturacion` | `-` | `String` | Código postal de facturación. | Cadena |
| `numeroTarjeta` | `-` | `String` | Número de tarjeta. | Cadena de dígitos |
| `vencimiento` | `-` | `Date` | Vencimiento de la tarjeta. | Fecha |
| `codigoSeguridad` | `-` | `String` | Código de seguridad. | 3 o 4 dígitos |
| `franquicia` | `-` | `String` | Franquicia de la tarjeta. | VISA, MASTERCARD, DINERS |
| `codigoDistribuidor` | `-` | `String [0..1]` | Código del distribuidor que refirió. | Cadena o nulo |
| `idSuscripcion` | `-` | `Integer [0..1]` | Suscripción a modificar; solo con PAQUETE_PLAN. | Entero o nulo |
| `identificadorExterno` | `-` | `String [0..1]` | sub verificado, tomado de la sesión por la vista (no del cliente HTTP). **(agregado en implementación, P-07)** | Obligatorio en registro; nulo en modificación |
| `nombre` | `-` | `String [0..1]` | Nombre del cliente (registro y categoría PERSONAL). **(agregado en implementación, P-07)** | Texto, máx. 120 |
| `correo` | `-` | `String [0..1]` | Correo verificado, tomado de la sesión por la vista. **(agregado en implementación, P-07)** | Obligatorio en registro; nulo en modificación |

### `EmpleadoDTO` — «DTO»
Módulo Python: `chibchaweb.servicio.dto`

Objeto de transferencia con los datos del formulario de alta y edición de empleados.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `nombre` | `-` | `String` | Nombre completo. | Cadena |
| `documento` | `-` | `String` | Documento de identidad. | Cadena |
| `correo` | `-` | `String` | Correo con el que el empleado ingresará. | Correo |
| `telefono` | `-` | `String` | Teléfono. | Cadena |
| `idRol` | `-` | `Integer` | Cargo asignado. | Id de Rol |

### `DistribuidorDTO` — «DTO»
Módulo Python: `chibchaweb.servicio.dto`

Objeto de transferencia con los datos del formulario de alta y edición de distribuidores.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `nombre` | `-` | `String` | Nombre completo. | Cadena |
| `documento` | `-` | `String` | Documento de identidad. | Cadena |
| `correo` | `-` | `String` | Correo de contacto. | Correo |
| `telefono` | `-` | `String` | Teléfono. | Cadena |

### `ResumenDTO` — «DTO»
Módulo Python: `chibchaweb.servicio.dto`

Objeto de transferencia con la vista resumida de un registro en un listado.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador del registro. | Entero |
| `titulo` | `-` | `String` | Texto principal de la fila. | Cadena |
| `subtitulo` | `-` | `String` | Texto secundario de la fila. | Cadena |
| `estado` | `-` | `String` | Estado del registro. | Cadena |

### `DetalleDTO` — «DTO»
Módulo Python: `chibchaweb.servicio.dto`

Objeto de transferencia con la vista ampliada de un registro.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador del registro. | Entero |
| `titulo` | `-` | `String` | Título de la vista. | Cadena |
| `campos` | `-` | `String [0..*]` | Pares etiqueta: valor a mostrar. | Cero o más |

### `ResultadoMigracionDTO` — «DTO»
Módulo Python: `chibchaweb.servicio.dto`

Objeto de transferencia con el resultado de la simulación de la migración.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `idProceso` | `-` | `Integer` | Proceso de migración creado. | Entero |
| `validos` | `-` | `Integer` | Registros válidos. | Entero ≥ 0 |
| `invalidos` | `-` | `Integer` | Registros inválidos. | Entero ≥ 0 |
| `entradas` | `-` | `String [0..*]` | Líneas del log para mostrar. | Cero o más |
