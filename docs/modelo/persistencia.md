# Capa de persistencia

Mapeadores de datos (Data Mapper con Layer Supertype). Cada mapeador concreto hereda de `Mapeador<T>` e **implementa la interfaz de repositorio del dominio**. Los servicios no los conocen: los recibe el contenedor de dependencias.

> Convenciones: visibilidad `-` privada, `+` pública, `#` protegida. La multiplicidad acompaña al tipo (`[0..*]`, `[1..*]`, `[0..1]`). Getters/setters no se listan: existe uno por atributo privado salvo en colecciones, que se manipulan solo con los métodos listados. Las subclases listan solo lo propio y lo que sobrescriben. En Python los nombres se traducen a `snake_case` de forma mecánica (`validarDatosFacturacion` → `validar_datos_facturacion`); las clases conservan su nombre.

## Capa de persistencia — Mapeadores

### `Mapeador` — abstracta · plantilla <T : class>
Módulo Python: `chibchaweb.persistencia.mapeadores`

Clase plantilla abstracta (parámetro T : class) que concentra las operaciones comunes de los mapeadores de datos (Data Mapper con Layer Supertype).

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `nombreTabla` | `#` | `String` | Tabla principal que mapea la subclase. | Nombre de tabla existente |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: T` | `Integer` | *(abstracto)* Inserta el objeto y devuelve su id. |
| `actualizar` | `+` | `objeto: T` | `void` | *(abstracto)* Actualiza el objeto. |
| `buscarPorId` | `+` | `id: Integer` | `T` | *(abstracto)* Reconstruye el objeto por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `T [0..*]` | *(abstracto)* Devuelve los objetos que coinciden con el filtro. |
| `existe` | `+` | `id: Integer` | `Boolean` | Indica si existe un registro con el id en nombreTabla. |

### `MapeadorUsuario` — hereda de `Mapeador<T → Usuario>` · implementa `RepositorioUsuario`
Módulo Python: `chibchaweb.persistencia.mapeadores`

Mapeador del agregado Usuario (cliente con direcciones, medio de pago y cuenta; empleado; distribuidor). Liga T → Usuario. Respalda los datos sensibles del cliente ante una caída.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `gestor` | `-` | `GestorContingencia` | Gestor de contingencia compartido (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: Usuario` | `Integer` | Inserta el usuario en usuario y en la tabla de su subtipo, con direcciones, medio de pago y cuenta; respalda en contingencia si la base falla. |
| `actualizar` | `+` | `objeto: Usuario` | `void` | Actualiza el agregado Usuario. Respalda en contingencia si la base de datos falla. |
| `buscarPorId` | `+` | `id: Integer` | `Usuario` | Reconstruye el agregado Usuario por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `Usuario [0..*]` | Lista los Usuario que coinciden con el filtro. |
| `buscarPorIdentificadorExterno` | `+` | `identificador: String` | `Usuario [0..1]` | Busca al usuario por su cuenta de acceso. |
| `buscarDistribuidorPorCodigo` | `+` | `codigo: String` | `Distribuidor [0..1]` | Busca un distribuidor activo por su código. |
| `inactivar` | `+` | `id: Integer` | `void` | Marca activo = false. |
| `buscarPorCorreo` | `+` | `correo: String` | `Usuario [0..1]` | Busca un usuario por correo (primer ingreso de empleados y migrados). |
| `buscarClientes` | `+` | `filtro: String` | `Cliente [0..*]` | Lista clientes que coinciden con el filtro. |
| `buscarEmpleados` | `+` | `filtro: String` | `Empleado [0..*]` | Lista empleados que coinciden con el filtro. |
| `buscarDistribuidores` | `+` | `filtro: String` | `Distribuidor [0..*]` | Lista distribuidores que coinciden con el filtro. |
| `restaurar` | `+` | `contenido: String` | `void` | Reinserta un agregado desde su contenido respaldado en contingencia (lo usa ServicioContingencia). **(agregado en implementación, P-05)** |

### `MapeadorSuscripcion` — hereda de `Mapeador<T → Suscripcion>` · implementa `RepositorioSuscripcion`
Módulo Python: `chibchaweb.persistencia.mapeadores`

Mapeador del agregado Suscripcion (con sitio web y pagos). Liga T → Suscripcion. Respalda los cobros ejecutados ante una caída.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `gestor` | `-` | `GestorContingencia` | Gestor de contingencia compartido (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: Suscripcion` | `Integer` | Inserta el agregado Suscripcion y devuelve su id. Respalda en contingencia si la base de datos falla. |
| `actualizar` | `+` | `objeto: Suscripcion` | `void` | Actualiza el agregado Suscripcion. Respalda en contingencia si la base de datos falla. |
| `buscarPorId` | `+` | `id: Integer` | `Suscripcion` | Reconstruye el agregado Suscripcion por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `Suscripcion [0..*]` | Lista los Suscripcion que coinciden con el filtro. |
| `buscarVencidas` | `+` | `fecha: Date` | `Suscripcion [0..*]` | Lista las suscripciones activas con corte vencido. |
| `registrarPago` | `+` | `pago: Pago` | `void` | Inserta un pago; respalda en contingencia si la base falla. |
| `buscarPagosParaComision` | `+` | `distribuidor: Distribuidor, inicio: Date, fin: Date` | `Pago [0..*]` | Lista los pagos disponibles de los referidos del distribuidor en el periodo. |
| `buscarSitio` | `+` | `id: Integer` | `SitioWeb` | Reconstruye un sitio web por su id. |
| `restaurar` | `+` | `contenido: String` | `void` | Reinserta un agregado desde su contenido respaldado en contingencia (lo usa ServicioContingencia). **(agregado en implementación, P-05)** |

### `MapeadorComision` — hereda de `Mapeador<T → Comision>` · implementa `RepositorioComision`
Módulo Python: `chibchaweb.persistencia.mapeadores`

Mapeador del agregado Comision (con cheque). Liga T → Comision. Respalda los cheques emitidos ante una caída.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `gestor` | `-` | `GestorContingencia` | Gestor de contingencia compartido (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: Comision` | `Integer` | Inserta el agregado Comision y devuelve su id. Respalda en contingencia si la base de datos falla. |
| `actualizar` | `+` | `objeto: Comision` | `void` | Actualiza el agregado Comision. Respalda en contingencia si la base de datos falla. |
| `buscarPorId` | `+` | `id: Integer` | `Comision` | Reconstruye el agregado Comision por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `Comision [0..*]` | Lista los Comision que coinciden con el filtro. |
| `registrarCheque` | `+` | `comision: Comision` | `void` | Inserta el cheque de la comisión; respalda en contingencia si la base falla. |
| `restaurar` | `+` | `contenido: String` | `void` | Reinserta un agregado desde su contenido respaldado en contingencia (lo usa ServicioContingencia). **(agregado en implementación, P-05)** |

### `MapeadorSolicitudDominio` — hereda de `Mapeador<T → SolicitudDominio>` · implementa `RepositorioSolicitudDominio`
Módulo Python: `chibchaweb.persistencia.mapeadores`

Mapeador de SolicitudDominio. Liga T → SolicitudDominio. Respalda las solicitudes ya enviadas ante una caída.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `gestor` | `-` | `GestorContingencia` | Gestor de contingencia compartido (inyectado). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: SolicitudDominio` | `Integer` | Inserta el agregado SolicitudDominio y devuelve su id. Respalda en contingencia si la base de datos falla. |
| `actualizar` | `+` | `objeto: SolicitudDominio` | `void` | Actualiza el agregado SolicitudDominio. Respalda en contingencia si la base de datos falla. |
| `buscarPorId` | `+` | `id: Integer` | `SolicitudDominio` | Reconstruye el agregado SolicitudDominio por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `SolicitudDominio [0..*]` | Lista los SolicitudDominio que coinciden con el filtro. |
| `buscarPorSolicitante` | `+` | `idCliente: Integer` | `SolicitudDominio [0..*]` | Lista las solicitudes de un cliente. |
| `restaurar` | `+` | `contenido: String` | `void` | Reinserta un agregado desde su contenido respaldado en contingencia (lo usa ServicioContingencia). **(agregado en implementación, P-05)** |

### `MapeadorTicket` — hereda de `Mapeador<T → Ticket>` · implementa `RepositorioTicket`
Módulo Python: `chibchaweb.persistencia.mapeadores`

Mapeador del agregado Ticket (con sus movimientos). Liga T → Ticket.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: Ticket` | `Integer` | Inserta el agregado Ticket y devuelve su id. |
| `actualizar` | `+` | `objeto: Ticket` | `void` | Actualiza el agregado Ticket. |
| `buscarPorId` | `+` | `id: Integer` | `Ticket` | Reconstruye el agregado Ticket por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `Ticket [0..*]` | Lista los Ticket que coinciden con el filtro. |
| `buscarCreadosEl` | `+` | `fecha: Date` | `Ticket [0..*]` | Lista los tickets creados en la fecha. |
| `buscarAbiertos` | `+` | `—` | `Ticket [0..*]` | Lista los tickets no resueltos. |
| `buscarPorReportante` | `+` | `idUsuario: Integer` | `Ticket [0..*]` | Lista los tickets de un usuario. |

### `MapeadorMigracion` — hereda de `Mapeador<T → ProcesoMigracion>` · implementa `RepositorioMigracion`
Módulo Python: `chibchaweb.persistencia.mapeadores`

Mapeador del agregado ProcesoMigracion (con su log). Liga T → ProcesoMigracion.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: ProcesoMigracion` | `Integer` | Inserta el agregado ProcesoMigracion y devuelve su id. |
| `actualizar` | `+` | `objeto: ProcesoMigracion` | `void` | Actualiza el agregado ProcesoMigracion. |
| `buscarPorId` | `+` | `id: Integer` | `ProcesoMigracion` | Reconstruye el agregado ProcesoMigracion por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `ProcesoMigracion [0..*]` | Lista los ProcesoMigracion que coinciden con el filtro. |

### `MapeadorCatalogo` — implementa `RepositorioCatalogo`
Módulo Python: `chibchaweb.persistencia.mapeadores`

Mapeador de solo lectura de los catálogos: paquetes, planes, franquicias, roles y niveles de servicio.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `listarPaquetes` | `+` | `—` | `PaqueteHosting [0..*]` | Lista los paquetes. |
| `buscarPaquete` | `+` | `id: Integer` | `PaqueteHosting` | Busca un paquete por id. |
| `listarPlanes` | `+` | `—` | `PlanPago [0..*]` | Lista los planes. |
| `buscarPlan` | `+` | `id: Integer` | `PlanPago` | Busca un plan por id. |
| `buscarFranquicia` | `+` | `nombre: String` | `Franquicia` | Busca una franquicia por nombre. |
| `buscarRol` | `+` | `id: Integer` | `Rol` | Busca un rol por id. |
| `buscarNivelInicial` | `+` | `—` | `NivelServicio` | Devuelve el nivel de orden 1. |
| `buscarNivelSiguiente` | `+` | `actual: NivelServicio` | `NivelServicio [0..1]` | Devuelve el nivel de orden siguiente o nulo si es el último. |
| `listarRoles` | `+` | `—` | `Rol [0..*]` | Lista los roles. |
