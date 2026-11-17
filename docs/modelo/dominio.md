# Modelo de dominio

Clases del dominio, interfaces de integración y de repositorio. **El dominio no importa nada de Django, DRF, persistencia, servicio ni adaptadores** (ver `arquitectura.md`).

> Convenciones: visibilidad `-` privada, `+` pública, `#` protegida. La multiplicidad acompaña al tipo (`[0..*]`, `[1..*]`, `[0..1]`). Getters/setters no se listan: existe uno por atributo privado salvo en colecciones, que se manipulan solo con los métodos listados. Las subclases listan solo lo propio y lo que sobrescriben. En Python los nombres se traducen a `snake_case` de forma mecánica (`validarDatosFacturacion` → `validar_datos_facturacion`); las clases conservan su nombre.

## Capa de dominio — Cuentas y Perfiles

### `Usuario` — «P» · abstracta
Módulo Python: `chibchaweb.dominio.cuentas`

Clase abstracta que reúne los datos comunes de toda persona registrada en el sistema (clientes, empleados y distribuidores) y su posible vínculo con un proveedor de autenticación externo. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `nombre` | `-` | `String` | Nombre completo; en clientes proviene del proveedor externo y no se edita. | Cadena no vacía, máx. 120 |
| `correo` | `-` | `String` | Correo electrónico de contacto y de vinculación de la cuenta. | Correo válido, único, máx. 120 |
| `telefono` | `-` | `String` | Teléfono de contacto. | Dígitos y espacios, máx. 20 |
| `activo` | `-` | `Boolean` | Indica si el usuario está vigente; la baja es lógica. | true / false |
| `fechaRegistro` | `-` | `Date` | Fecha y hora de alta del usuario. | Fecha-hora no futura |
| `fechaModificacion` | `-` | `Date` | Fecha y hora de la última modificación. | Fecha-hora ≥ fechaRegistro |
| `cuenta` | `-` | `CuentaAcceso [0..1]` | Cuenta de acceso con el proveedor externo (rol cuenta). | Nula en distribuidores |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `esAutenticable` | `+` | `—` | `Boolean` | *(abstracto)* Indica si el tipo de usuario puede ingresar al sistema; cada subclase lo resuelve. |
| `vincularCuenta` | `+` | `identidad: IdentidadExterna` | `void` | Crea la CuentaAcceso con el identificador verificado; falla si el usuario no es autenticable o ya tiene cuenta. |
| `inactivar` | `+` | `—` | `void` | Realiza la baja lógica del usuario (activo = false). |

### `Cliente` — «P» · hereda de `Usuario`
Módulo Python: `chibchaweb.dominio.cuentas`

Usuario que contrata el hospedaje. Se autoregistra, conserva sus direcciones y su medio de pago, y puede haber sido referido por un distribuidor. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `residencia` | `-` | `Direccion` | Dirección de residencia (rol residencia). | Referencia obligatoria |
| `facturacion` | `-` | `Direccion` | Dirección de facturación (rol facturacion). | Referencia obligatoria, distinta de residencia |
| `medioPago` | `-` | `MedioPago` | Medio de pago con el que se cobra (rol medioPago). | Referencia obligatoria |
| `distribuidor` | `-` | `Distribuidor [0..1]` | Distribuidor que refirió al cliente (rol distribuidor). | Nula si no hubo código válido |
| `suscripciones` | `-` | `Suscripcion [1..*]` | Suscripciones de hospedaje del cliente (rol suscripciones). | Al menos una |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `esAutenticable` | `+` | `—` | `Boolean` | Devuelve verdadero: el cliente ingresa con su cuenta externa. |
| `asociarDistribuidor` | `+` | `distribuidor: Distribuidor` | `void` | Vincula al cliente con el distribuidor que lo refirió. |
| `validarDatosFacturacion` | `+` | `validador: ValidadorMedioPago` | `Boolean` | Valida las dos direcciones y delega en el medio de pago su validación antes de persistir (RF01). |
| `agregarSuscripcion` | `+` | `suscripcion: Suscripcion` | `void` | Añade una suscripción a la colección. |
| `cancelarSuscripcion` | `+` | `suscripcion: Suscripcion` | `void` | Suspende y retira una suscripción de la colección. |

### `Empleado` — «P» · hereda de `Usuario`
Módulo Python: `chibchaweb.dominio.cuentas`

Usuario del personal interno de ChibchaWEB. Sus permisos dependen del rol asignado (gestión, soporte o administrador). Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `documento` | `-` | `String` | Documento de identidad. | Alfanumérico único, máx. 20 |
| `rol` | `-` | `Rol` | Cargo asignado (rol rol). | Referencia obligatoria a un Rol |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `esAutenticable` | `+` | `—` | `Boolean` | Devuelve verdadero: el empleado ingresa con su cuenta externa. |
| `cambiarRol` | `+` | `nuevo: Rol` | `void` | Reasigna el cargo del empleado. |
| `puedeRealizar` | `+` | `operacion: String` | `Boolean` | Consulta en su rol si la operación está permitida. |

### `Distribuidor` — «P» · hereda de `Usuario`
Módulo Python: `chibchaweb.dominio.cuentas`

Usuario que refiere clientes a ChibchaWEB a cambio de una comisión. No se autentica en el sistema: lo administra el personal de gestión. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `documento` | `-` | `String` | Documento de identidad, requerido para emitir el cheque. | Alfanumérico único, máx. 20 |
| `codigo` | `-` | `String` | Código que los clientes ingresan al registrarse. | Alfanumérico único, máx. 20, generado por el sistema |
| `referidos` | `-` | `Cliente [0..*]` | Clientes registrados con su código (rol referidos). | Cero o más |
| `comisiones` | `-` | `Comision [0..*]` | Comisiones liquidadas (rol comisiones). | Cero o más |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `esAutenticable` | `+` | `—` | `Boolean` | Devuelve falso: el distribuidor no ingresa al sistema. |
| `agregarReferido` | `+` | `cliente: Cliente` | `void` | Añade un cliente a sus referidos. |
| `cantidadReferidos` | `+` | `—` | `Integer` | Cuenta los clientes referidos. |
| `agregarComision` | `+` | `comision: Comision` | `void` | Añade una comisión liquidada. |
| `determinarCategoria` | `+` | `categorias: CategoriaDistribuidor [1..*]` | `CategoriaDistribuidor` | Recorre las estrategias y devuelve la que aplica a su cantidad de referidos. |

### `CuentaAcceso` — «P»
Módulo Python: `chibchaweb.dominio.cuentas`

Vínculo entre un usuario y su identidad en el proveedor de autenticación externo (OAuth 2.0). Permite reconocer al usuario en cada ingreso. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `identificadorExterno` | `-` | `String` | Identificador estable (sub) del usuario en el proveedor. | Cadena no vacía, máx. 255; única por proveedor |
| `proveedor` | `-` | `String` | Nombre del proveedor de autenticación. | Cadena no vacía, máx. 50 |
| `fechaVinculacion` | `-` | `Date` | Fecha y hora en que se vinculó la cuenta. | Fecha-hora |
| `ultimoAcceso` | `-` | `Date` | Fecha y hora del último ingreso. | Fecha-hora o nulo |
| `titular` | `-` | `Usuario` | Usuario dueño de la cuenta (rol titular). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `coincideCon` | `+` | `identificadorExterno: String` | `Boolean` | Compara un identificador externo con el de la cuenta. |
| `registrarAcceso` | `+` | `—` | `void` | Actualiza la fecha del último acceso. |

### `Rol` — «P»
Módulo Python: `chibchaweb.dominio.cuentas`

Cargo de un empleado con el conjunto de operaciones que tiene permitido realizar. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `nombre` | `-` | `String` | Nombre del cargo. | Gestión, Soporte, Administrador |
| `operaciones` | `-` | `String [0..*]` | Operaciones permitidas al cargo. | Cero o más nombres de operación, sin repetir |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `otorgar` | `+` | `operacion: String` | `void` | Añade una operación permitida. |
| `revocar` | `+` | `operacion: String` | `void` | Retira una operación permitida. |
| `permite` | `+` | `operacion: String` | `Boolean` | Indica si la operación está permitida. |

### `Direccion` — «P»
Módulo Python: `chibchaweb.dominio.cuentas`

Dirección postal de un cliente; cada cliente tiene una de residencia y una de facturación. Persistente con tabla propia (Foreign Key Mapping).

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `linea` | `-` | `String` | Calle, número y complemento. | Cadena no vacía, máx. 150 |
| `ciudad` | `-` | `String` | Ciudad. | Cadena no vacía, máx. 80 |
| `codigoPostal` | `-` | `String` | Código postal. | Alfanumérico, máx. 10 |
| `pais` | `-` | `String` | País. | Cadena no vacía, máx. 60 |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `validar` | `+` | `—` | `Boolean` | Verifica que los campos obligatorios estén completos y con formato válido. |

### `MedioPago` — «P» · abstracta
Módulo Python: `chibchaweb.dominio.cuentas`

Clase abstracta para los medios con los que se cobra a un cliente. Permite incorporar nuevos medios (p. ej. cheques personales) sin modificar Cliente ni Suscripcion (Strategy por polimorfismo). Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `validar` | `+` | `validador: ValidadorMedioPago` | `Boolean` | *(abstracto)* Valida el medio de pago con el verificador externo. |
| `estaVigente` | `+` | `—` | `Boolean` | *(abstracto)* Indica si el medio puede usarse para cobrar. |
| `descripcion` | `+` | `—` | `String` | *(abstracto)* Devuelve una representación segura del medio para mostrar. |

### `TarjetaCredito` — «P» · hereda de `MedioPago`
Módulo Python: `chibchaweb.dominio.cuentas`

Medio de pago basado en tarjeta de crédito de una franquicia aceptada. Implementa la validación local (franquicia y vigencia) y delega la verificación externa. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `numero` | `-` | `String` | Número de la tarjeta; se almacena cifrado. | 13 a 19 dígitos que cumplan el patrón de la franquicia |
| `vencimiento` | `-` | `Date` | Fecha de vencimiento. | Mes/año no vencido al registrar |
| `codigoSeguridad` | `-` | `String` | Código de verificación; solo se usa para validar, no se persiste ni se respalda. | 3 o 4 dígitos |
| `franquicia` | `-` | `Franquicia` | Franquicia de la tarjeta (rol franquicia). | VISA, MASTERCARD o DINERS |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `validar` | `+` | `validador: ValidadorMedioPago` | `Boolean` | Comprueba que la franquicia reconozca el número y que esté vigente; luego pide la verificación externa con validador.verificar(this). |
| `estaVigente` | `+` | `—` | `Boolean` | Indica si la fecha de vencimiento no ha pasado. |
| `descripcion` | `+` | `—` | `String` | Devuelve el número enmascarado (franquicia y últimos cuatro dígitos). |

### `Franquicia` — «P»
Módulo Python: `chibchaweb.dominio.cuentas`

Catálogo de franquicias de tarjeta aceptadas (VISA, MASTERCARD, DINERS), con el patrón que reconoce sus números. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `nombre` | `-` | `String` | Nombre de la franquicia. | VISA, MASTERCARD, DINERS |
| `patronNumero` | `-` | `String` | Expresión regular que reconoce los números de la franquicia. | Expresión regular válida, máx. 100 |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `reconoceNumero` | `+` | `numero: String` | `Boolean` | Indica si el número cumple el patrón de la franquicia. |

## Capa de dominio — Hospedaje

### `PaqueteHosting` — «P»
Módulo Python: `chibchaweb.dominio.hospedaje`

Catálogo de paquetes de hospedaje (Chibcha-Plata, Chibcha-Oro, Chibcha-Platino) con su tarifa mensual en USD. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `nombre` | `-` | `String` | Nombre comercial del paquete. | Chibcha-Plata, Chibcha-Oro, Chibcha-Platino |
| `tarifaMensual` | `-` | `Decimal` | Tarifa mensual de lista en USD. | Decimal > 0 (5.00, 10.00, 20.00) |
| `descripcion` | `-` | `String` | Descripción del paquete. | Texto libre |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `calcularMonto` | `+` | `plan: PlanPago` | `Decimal` | Calcula tarifa × meses del plan con el descuento del plan aplicado. |

### `PlanPago` — «P»
Módulo Python: `chibchaweb.dominio.hospedaje`

Catálogo de planes de pago (mensual, trimestral, semestral, anual) con su duración y descuento por compromiso. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `nombre` | `-` | `String` | Nombre del plan. | Mensual, Trimestral, Semestral, Anual |
| `meses` | `-` | `Integer` | Duración del periodo de cobro. | 1, 3, 6 o 12 |
| `descuento` | `-` | `Decimal` | Descuento por compromiso. | 0.00 a 1.00 (0, 0.05, 0.10, 0.15) |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `aplicarDescuento` | `+` | `monto: Decimal` | `Decimal` | Devuelve el monto con el descuento del plan. |

### `SitioWeb` — «P»
Módulo Python: `chibchaweb.dominio.hospedaje`

Sitio hospedado de un cliente: subdominio asignado, dominio propio opcional y plataforma. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `subdominio` | `-` | `String` | Subdominio asignado por defecto (nombre.chibchaweb.com). | Cadena única, máx. 120 |
| `dominioPropio` | `-` | `String [0..1]` | Dominio propio, si el cliente lo registró. | Nombre de dominio único o nulo |
| `plataforma` | `-` | `Plataforma` | Plataforma de hospedaje. | Valores de Plataforma |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `asignarDominioPropio` | `+` | `dominio: String` | `void` | Asocia un dominio propio al sitio. |
| `tieneDominioPropio` | `+` | `—` | `Boolean` | Indica si el sitio tiene dominio propio. |

### `Suscripcion` — «P»
Módulo Python: `chibchaweb.dominio.hospedaje`

Contrato de hospedaje de un cliente: une sitio, paquete y plan, y lleva el ciclo de cobro (fecha de corte y pagos). Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `fechaInicio` | `-` | `Date` | Fecha de inicio del servicio. | Fecha |
| `fechaCorte` | `-` | `Date` | Próxima fecha de cobro. | Fecha ≥ fechaInicio |
| `activa` | `-` | `Boolean` | Indica si la suscripción está vigente. | true / false |
| `titular` | `-` | `Cliente` | Cliente dueño (rol titular). | Referencia obligatoria |
| `sitio` | `-` | `SitioWeb` | Sitio hospedado (rol sitio). | Referencia obligatoria, única |
| `paquete` | `-` | `PaqueteHosting` | Paquete contratado (rol paquete). | Referencia obligatoria |
| `plan` | `-` | `PlanPago` | Plan de pago contratado (rol plan). | Referencia obligatoria |
| `pagos` | `-` | `Pago [0..*]` | Historial de cobros (rol pagos). | Cero o más |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `montoDelPeriodo` | `+` | `—` | `Decimal` | Pide al paquete el monto del periodo según el plan. |
| `estaVencida` | `+` | `fecha: Date` | `Boolean` | Indica si la fecha de corte llegó en la fecha dada. |
| `avanzarCorte` | `+` | `—` | `void` | Mueve la fecha de corte según los meses del plan, tras un cobro exitoso. |
| `cambiarPaquete` | `+` | `nuevo: PaqueteHosting` | `void` | Cambia el paquete contratado. |
| `cambiarPlan` | `+` | `nuevo: PlanPago` | `void` | Cambia el plan de pago. |
| `agregarPago` | `+` | `pago: Pago` | `void` | Añade un pago al historial. |
| `suspender` | `+` | `—` | `void` | Marca la suscripción como inactiva. |
| `cobrar` | `+` | `pasarela: PasarelaPago` | `Pago` | Cobra el monto del periodo al medio de pago del titular, crea el Pago exitoso o fallido, lo agrega y avanza el corte si fue exitoso. |

### `Plataforma` — «enumeration»
Módulo Python: `chibchaweb.dominio.hospedaje`

Enumeración de las plataformas de hospedaje ofrecidas.

| Literal | Descripción |
|---|---|
| `WINDOWS` | Hospedaje sobre Windows. |
| `UNIX` | Hospedaje sobre Unix. |

## Capa de dominio — Facturación y Comisiones

### `Pago` — «P»
Módulo Python: `chibchaweb.dominio.facturacion`

Resultado de un intento de cobro periódico sobre una suscripción, exitoso o fallido. Los pagos exitosos sustentan las comisiones. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `monto` | `-` | `Decimal` | Monto cobrado en USD. | Decimal > 0 |
| `fecha` | `-` | `Date` | Fecha y hora del intento de cobro. | Fecha-hora |
| `estado` | `-` | `EstadoPago` | Resultado del cobro. | Valores de EstadoPago |
| `referenciaFranquicia` | `-` | `String [0..1]` | Referencia devuelta por el procesador. | Cadena, máx. 100; nula si el cobro falló |
| `comisionado` | `-` | `Boolean` | Indica si el pago ya sustentó una comisión. | true / false |
| `suscripcion` | `-` | `Suscripcion` | Suscripción cobrada (rol suscripcion). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `esExitoso` | `+` | `—` | `Boolean` | Indica si el cobro fue exitoso. |
| `estaDisponibleParaComision` | `+` | `—` | `Boolean` | Indica si es exitoso y aún no sustenta una comisión. |
| `marcarComisionado` | `+` | `—` | `void` | Marca el pago como usado en una comisión. |

### `Comision` — «P»
Módulo Python: `chibchaweb.dominio.facturacion`

Liquidación de un periodo para un distribuidor. Conserva la categoría y el porcentaje aplicados como constancia histórica. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `fechaInicio` | `-` | `Date` | Inicio del periodo liquidado. | Fecha |
| `fechaFin` | `-` | `Date` | Fin del periodo liquidado. | Fecha ≥ fechaInicio |
| `clientesReferidos` | `-` | `Integer` | Clientes referidos contados en la liquidación. | Entero ≥ 0 |
| `nombreCategoria` | `-` | `String` | Categoría aplicada (constancia histórica). | Básico o Premium |
| `porcentaje` | `-` | `Decimal` | Porcentaje aplicado (constancia histórica). | 0.10 o 0.15 |
| `beneficiario` | `-` | `Distribuidor` | Distribuidor que recibe la comisión (rol beneficiario). | Referencia obligatoria |
| `pagosBase` | `-` | `Pago [1..*]` | Pagos exitosos que sustentan la comisión (rol pagosBase). | Al menos uno |
| `cheque` | `-` | `Cheque [0..1]` | Cheque emitido (rol cheque). | Nulo hasta emitirse |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `agregarPagoBase` | `+` | `pago: Pago` | `void` | Añade un pago disponible y lo marca como comisionado. |
| `calcularMonto` | `+` | `—` | `Decimal` | Suma los pagos base y aplica el porcentaje. |
| `asociarCheque` | `+` | `cheque: Cheque` | `void` | Asocia el cheque emitido. |
| `tieneCheque` | `+` | `—` | `Boolean` | Indica si ya se emitió el cheque. |

### `Cheque` — «P»
Módulo Python: `chibchaweb.dominio.facturacion`

Cheque emitido a nombre de un distribuidor por el monto de una comisión. Su emisión es irreversible. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `numero` | `-` | `String` | Número del cheque. | Alfanumérico único, máx. 30 |
| `beneficiario` | `-` | `String` | Nombre del distribuidor copiado al emitir. | Cadena no vacía, máx. 120 |
| `monto` | `-` | `Decimal` | Monto del cheque en USD. | Decimal > 0 |
| `fechaEmision` | `-` | `Date` | Fecha de emisión. | Fecha |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `montoEnLetras` | `+` | `—` | `String` | Devuelve el monto escrito en letras para imprimir el cheque. |

### `CategoriaDistribuidor` — «interface»
Módulo Python: `chibchaweb.dominio.facturacion`

Interfaz de la estrategia que determina la categoría del distribuidor y su porcentaje de comisión (patrón Strategy).

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `nombre` | `+` | `—` | `String` | Devuelve el nombre de la categoría. |
| `porcentaje` | `+` | `—` | `Decimal` | Devuelve el porcentaje de comisión. |
| `aplicaA` | `+` | `cantidadReferidos: Integer` | `Boolean` | Indica si la categoría corresponde a la cantidad de referidos. |

### `CategoriaBasica` — implementa `CategoriaDistribuidor`
Módulo Python: `chibchaweb.dominio.facturacion`

Estrategia de categoría Básica: hasta 100 clientes referidos, comisión del 10 %.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `porcentajeComision` | `-` | `Decimal = 0.10` | Porcentaje de comisión de la categoría. | Constante 0.10 |
| `limiteSuperior` | `-` | `Integer = 100` | Máximo de clientes referidos de la categoría. | Constante 100 |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `nombre` | `+` | `—` | `String` | Devuelve "Básico". |
| `porcentaje` | `+` | `—` | `Decimal` | Devuelve 0.10. |
| `aplicaA` | `+` | `cantidadReferidos: Integer` | `Boolean` | Verdadero si la cantidad es ≤ 100. |

### `CategoriaPremium` — implementa `CategoriaDistribuidor`
Módulo Python: `chibchaweb.dominio.facturacion`

Estrategia de categoría Premium: más de 100 clientes referidos, comisión del 15 %.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `porcentajeComision` | `-` | `Decimal = 0.15` | Porcentaje de comisión de la categoría. | Constante 0.15 |
| `limiteInferior` | `-` | `Integer = 101` | Mínimo de clientes referidos de la categoría. | Constante 101 |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `nombre` | `+` | `—` | `String` | Devuelve "Premium". |
| `porcentaje` | `+` | `—` | `Decimal` | Devuelve 0.15. |
| `aplicaA` | `+` | `cantidadReferidos: Integer` | `Boolean` | Verdadero si la cantidad es ≥ 101. |

### `EstadoPago` — «enumeration»
Módulo Python: `chibchaweb.dominio.facturacion`

Enumeración de los resultados posibles de un cobro.

| Literal | Descripción |
|---|---|
| `EXITOSO` | El procesador aprobó el cargo. |
| `FALLIDO` | El cargo fue rechazado o no se completó. |

## Capa de dominio — Dominios Web

### `SolicitudDominio` — «P»
Módulo Python: `chibchaweb.dominio.dominios_web`

Solicitud de registro de un dominio propio hecha por un cliente. Actúa como director del Builder que arma el documento y registra el resultado del envío. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `nombre` | `-` | `String` | Nombre del dominio sin extensión. | Alfanumérico y guiones, sin guion inicial ni final, máx. 63 |
| `extension` | `-` | `String` | Extensión del dominio. | Extensión admitida (.com, .co, .net, .org) |
| `fechaSolicitud` | `-` | `Date` | Fecha y hora de la solicitud. | Fecha-hora |
| `fechaEnvio` | `-` | `Date [0..1]` | Fecha y hora del envío al registrador. | Fecha-hora o nulo |
| `estado` | `-` | `EstadoSolicitud` | Estado de la solicitud. | Valores de EstadoSolicitud |
| `solicitante` | `-` | `Cliente` | Cliente que solicita (rol solicitante). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `nombreCompleto` | `+` | `—` | `String` | Devuelve nombre más extensión. |
| `validarFormato` | `+` | `—` | `Boolean` | Valida el nombre (alfanumérico y guiones, sin guion inicial ni final, máx. 63) y que la extensión esté admitida. |
| `estaPendiente` | `+` | `—` | `Boolean` | Indica si la solicitud aún no se ha enviado. |
| `marcarEnviada` | `-` | `fecha: Date` | `void` | Cambia el estado a ENVIADA y registra la fecha de envío. |
| `marcarFallida` | `-` | `—` | `void` | Cambia el estado a FALLIDA. |
| `construirDocumento` | `+` | `constructor: ConstructorSolicitud` | `String` | Actúa como director del Builder: invoca los pasos del constructor con sus datos y devuelve el resultado. |
| `enviarA` | `+` | `registrador: RegistradorDominio, documento: String` | `void` | Envía el documento con el registrador y marca la solicitud como enviada o fallida. |

### `ConstructorSolicitud` — «interface»
Módulo Python: `chibchaweb.dominio.dominios_web`

Interfaz del constructor que arma por partes el documento de la solicitud de dominio (patrón Builder).

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `iniciarDocumento` | `+` | `—` | `void` | Inicia un documento vacío. |
| `agregarSolicitante` | `+` | `cliente: Cliente` | `void` | Agrega los datos del solicitante. |
| `agregarDominio` | `+` | `nombre: String, extension: String` | `void` | Agrega el dominio solicitado. |
| `agregarFecha` | `+` | `fecha: Date` | `void` | Agrega la fecha de la solicitud. |
| `obtenerResultado` | `+` | `—` | `String` | Devuelve el documento terminado. |

### `ConstructorXML` — implementa `ConstructorSolicitud`
Módulo Python: `chibchaweb.dominio.dominios_web`

Constructor concreto que produce el documento XML con el formato definido por ChibchaWEB para los registradores.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `contenido` | `-` | `String` | Documento XML en construcción. | Texto XML; vacío al iniciar |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `iniciarDocumento` | `+` | `—` | `void` | Inicia el XML con su encabezado. |
| `agregarSolicitante` | `+` | `cliente: Cliente` | `void` | Agrega el elemento del solicitante. |
| `agregarDominio` | `+` | `nombre: String, extension: String` | `void` | Agrega el elemento del dominio. |
| `agregarFecha` | `+` | `fecha: Date` | `void` | Agrega el elemento de fecha. |
| `obtenerResultado` | `+` | `—` | `String` | Cierra y devuelve el XML. |

### `EstadoSolicitud` — «enumeration»
Módulo Python: `chibchaweb.dominio.dominios_web`

Enumeración de los estados de una solicitud de dominio.

| Literal | Descripción |
|---|---|
| `REGISTRADA` | Capturada y validada, pendiente de envío. |
| `ENVIADA` | Entregada al registrador externo. |
| `FALLIDA` | El envío no se completó (p. ej. falla de red). |

## Capa de dominio — Soporte

### `Ticket` — «P»
Módulo Python: `chibchaweb.dominio.soporte`

Novedad técnica reportada por un usuario. Registra su nivel de servicio actual y la trazabilidad de sus cambios. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `descripcion` | `-` | `String` | Descripción del problema. | Texto no vacío |
| `fechaCreacion` | `-` | `Date` | Fecha y hora del reporte. | Fecha-hora |
| `categoria` | `-` | `CategoriaTicket` | Tipo de novedad. | Valores de CategoriaTicket |
| `estado` | `-` | `EstadoTicket` | Estado actual. | Valores de EstadoTicket |
| `reportante` | `-` | `Usuario` | Usuario que reporta (rol reportante). | Referencia obligatoria |
| `sitioAfectado` | `-` | `SitioWeb [0..1]` | Sitio afectado (rol sitioAfectado). | Nulo si la novedad no es de un sitio |
| `nivelActual` | `-` | `NivelServicio` | Nivel de servicio que atiende (rol nivelActual). | Referencia obligatoria |
| `movimientos` | `-` | `MovimientoTicket [0..*]` | Trazabilidad de cambios (rol movimientos). | Cero o más |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `escalar` | `+` | `siguiente: NivelServicio, responsable: Empleado, observacion: String` | `void` | Valida que el ticket esté abierto y que el nivel actual pueda escalar al siguiente; cambia el nivel y registra el movimiento. |
| `resolver` | `+` | `responsable: Empleado, observacion: String` | `void` | Marca el ticket como resuelto y registra el movimiento. |
| `estaAbierto` | `+` | `—` | `Boolean` | Indica si el ticket no está resuelto. |
| `ultimoMovimiento` | `+` | `—` | `MovimientoTicket` | Devuelve el movimiento más reciente. |

### `MovimientoTicket` — «P»
Módulo Python: `chibchaweb.dominio.soporte`

Registro de un cambio de estado o de nivel de un ticket, con su responsable. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `fecha` | `-` | `Date` | Fecha y hora del cambio. | Fecha-hora |
| `observacion` | `-` | `String` | Observación del responsable. | Texto libre |
| `estadoResultante` | `-` | `EstadoTicket` | Estado del ticket tras el cambio. | Valores de EstadoTicket |
| `nivelResultante` | `-` | `NivelServicio` | Nivel del ticket tras el cambio (rol nivelResultante). | Referencia obligatoria |
| `responsable` | `-` | `Empleado` | Empleado que registra el cambio (rol responsable). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `resultaEnResolucion` | `+` | `—` | `Boolean` | Indica si el movimiento resolvió el ticket. |

### `NivelServicio` — «P»
Módulo Python: `chibchaweb.dominio.soporte`

Catálogo ordenado de niveles de atención (soporte, gestión, desarrollo) por los que se escala un ticket. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `nombre` | `-` | `String` | Nombre del nivel. | Soporte, Gestión, Desarrollo |
| `orden` | `-` | `Integer` | Posición en la secuencia de escalamiento. | Entero ≥ 1, único |
| `esUltimo` | `-` | `Boolean` | Indica si es el último nivel. | true / false |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `puedeEscalar` | `+` | `—` | `Boolean` | Indica si existe un nivel siguiente. |
| `precede` | `+` | `otro: NivelServicio` | `Boolean` | Indica si este nivel va antes que otro. |

### `CategoriaTicket` — «enumeration»
Módulo Python: `chibchaweb.dominio.soporte`

Enumeración de los tipos de novedad que puede reportar un usuario.

| Literal | Descripción |
|---|---|
| `RENDIMIENTO` | Lentitud o caída del sitio. |
| `CORREO` | Problemas con el correo. |
| `BASE_DATOS` | Problemas con la base de datos del sitio. |
| `DOMINIO` | Problemas con el dominio. |
| `OTRA` | Novedad no asociada a las anteriores. |

### `EstadoTicket` — «enumeration»
Módulo Python: `chibchaweb.dominio.soporte`

Enumeración de los estados de un ticket.

| Literal | Descripción |
|---|---|
| `ABIERTO` | Registrado, en atención en el nivel actual. |
| `ESCALADO` | Pasado al siguiente nivel. |
| `RESUELTO` | Solucionado; no admite más cambios. |

## Capa de dominio — Migración

### `ProcesoMigracion` — «P»
Módulo Python: `chibchaweb.dominio.migracion`

Ejecución de la migración del sistema legado en dos fases (simulación y ejecución real) con punto de control manual. Persistente (los registros leídos no se persisten).

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `fechaInicio` | `-` | `Date` | Fecha y hora de inicio. | Fecha-hora |
| `fechaFin` | `-` | `Date [0..1]` | Fecha y hora de finalización. | Fecha-hora o nulo |
| `estado` | `-` | `EstadoMigracion` | Estado del proceso. | Valores de EstadoMigracion |
| `ejecutor` | `-` | `Empleado` | Administrador que ejecuta (rol ejecutor). | Referencia obligatoria |
| `registros` | `-` | `RegistroLegado [0..*]` | Registros leídos del sistema legado (rol registros); no persistentes. | Cero o más |
| `log` | `-` | `EntradaLog [0..*]` | Entradas del log (rol log). | Cero o más |
| `creadores` | `-` | `CreadorRegistroLegado [1..*]` | Creadores del Factory Method, uno por tipo de registro (rol creadores); no persistentes. | Al menos uno |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `simular` | `+` | `fuente: FuenteLegada` | `void` | Lee la fuente, crea cada registro con su creador, lo valida y llena el log sin escribir datos. |
| `agregarEntrada` | `+` | `entrada: EntradaLog` | `void` | Añade una entrada al log. |
| `cantidadValidos` | `+` | `—` | `Integer` | Cuenta los registros válidos. |
| `cantidadInvalidos` | `+` | `—` | `Integer` | Cuenta los registros inválidos. |
| `aprobar` | `+` | `—` | `void` | Pasa a APROBADA; solo desde SIMULADA. |
| `cancelar` | `+` | `—` | `void` | Pasa a CANCELADA. |
| `puedeEjecutarse` | `+` | `—` | `Boolean` | Indica si el proceso está aprobado. |
| `marcarEjecutado` | `+` | `—` | `void` | Pasa a EJECUTADA y registra la fecha de fin. |
| `marcarRevertido` | `+` | `—` | `void` | Pasa a REVERTIDA y registra la fecha de fin. |
| `prepararEjecucion` | `+` | `fuente: FuenteLegada` | `void` | Vuelve a leer y crear los registros sin escribir en el log y verifica que los válidos coincidan con la simulación. |

### `EntradaLog` — «P»
Módulo Python: `chibchaweb.dominio.migracion`

Línea del log de una migración: resultado de validar un registro o mensaje del proceso. Persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `id` | `-` | `Integer` | Identificador único asignado por la base de datos (Identity Field). | Entero positivo, autoincremental |
| `fecha` | `-` | `Date` | Fecha y hora de la entrada. | Fecha-hora |
| `nivel` | `-` | `NivelLog` | Severidad. | Valores de NivelLog |
| `mensaje` | `-` | `String` | Mensaje de la entrada. | Texto no vacío |
| `identificadorLegado` | `-` | `String [0..1]` | Identificador del registro legado asociado. | Cadena, máx. 50, o nulo |
| `tipoRegistro` | `-` | `String [0..1]` | Tipo del registro legado asociado. | CLIENTE, HOSTING, PAGO o nulo |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `esError` | `+` | `—` | `Boolean` | Indica si la entrada es de nivel ERROR. |

### `RegistroLegado` — abstracta
Módulo Python: `chibchaweb.dominio.migracion`

Clase abstracta para un registro leído del sistema legado; cada subtipo aplica sus propias reglas de validación. Producto abstracto del Factory Method. No persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `identificadorLegado` | `-` | `String` | Identificador del registro en el sistema legado. | Cadena no vacía |
| `valido` | `-` | `Boolean` | Resultado de la última validación. | true / false |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `validar` | `+` | `—` | `Boolean` | *(abstracto)* Aplica las reglas del subtipo y actualiza valido. |
| `describirErrores` | `+` | `—` | `String` | Describe los errores encontrados en la validación. |

### `ClienteLegado` — hereda de `RegistroLegado`
Módulo Python: `chibchaweb.dominio.migracion`

Registro legado con los datos de un cliente. No persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `nombre` | `-` | `String` | Nombre del cliente. | Cadena |
| `correo` | `-` | `String` | Correo del cliente. | Cadena; se valida formato |
| `direccion` | `-` | `String` | Dirección en formato libre del legado. | Cadena |
| `numeroTarjeta` | `-` | `String` | Número de tarjeta registrado. | Cadena; se valida contra la franquicia |
| `telefono` | `-` | `String` | Teléfono. | Cadena |
| `vencimientoTarjeta` | `-` | `Date` | Vencimiento de la tarjeta. | Fecha |
| `franquicia` | `-` | `String` | Franquicia de la tarjeta. | Cadena; debe existir en el catálogo |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `validar` | `+` | `—` | `Boolean` | Valida correo, dirección y tarjeta. |
| `aCliente` | `+` | `—` | `Cliente` | Construye el Cliente con sus direcciones y tarjeta. |

### `HostingLegado` — hereda de `RegistroLegado`
Módulo Python: `chibchaweb.dominio.migracion`

Registro legado de un servicio de hospedaje; su validación contra el catálogo actual garantiza la confiabilidad exigida en RF08. No persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `identificadorCliente` | `-` | `String` | Identificador legado del cliente dueño. | Cadena; debe existir entre los clientes migrados |
| `subdominio` | `-` | `String` | Subdominio del sitio. | Cadena única |
| `paquete` | `-` | `String` | Nombre del paquete en el legado. | Debe existir en el catálogo de paquetes |
| `plan` | `-` | `String` | Nombre del plan en el legado. | Debe existir en el catálogo de planes |
| `plataforma` | `-` | `String` | Plataforma del sitio. | WINDOWS o UNIX |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `validar` | `+` | `—` | `Boolean` | Valida que paquete, plan y plataforma existan en el catálogo actual. |
| `aSuscripcion` | `+` | `titular: Cliente, paquete: PaqueteHosting, plan: PlanPago` | `Suscripcion` | Construye la Suscripcion y su SitioWeb. |

### `PagoLegado` — hereda de `RegistroLegado`
Módulo Python: `chibchaweb.dominio.migracion`

Registro legado del historial de pagos de un cliente. No persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `identificadorCliente` | `-` | `String` | Identificador legado del cliente. | Cadena; debe existir entre los clientes migrados |
| `monto` | `-` | `Decimal` | Monto pagado. | Decimal > 0 |
| `fecha` | `-` | `Date` | Fecha del pago. | Fecha no futura |
| `referencia` | `-` | `String` | Referencia del pago en el legado. | Cadena |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `validar` | `+` | `—` | `Boolean` | Valida monto y fecha. |
| `aPago` | `+` | `suscripcion: Suscripcion` | `Pago` | Construye el Pago exitoso, marcado como comisionado. |

### `CreadorRegistroLegado` — abstracta
Módulo Python: `chibchaweb.dominio.migracion`

Creador abstracto del Factory Method: declara el método fábrica que instancia el subtipo de registro legado correspondiente. No persistente.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `tipo` | `+` | `—` | `String` | *(abstracto)* Devuelve el tipo de registro que atiende. |
| `crearRegistro` | `+` | `datos: String` | `RegistroLegado` | *(abstracto)* Método fábrica: instancia el subtipo de registro. |
| `procesar` | `+` | `datos: String` | `RegistroLegado` | Crea el registro con el método fábrica, lo valida y lo devuelve. |

### `CreadorClienteLegado` — hereda de `CreadorRegistroLegado`
Módulo Python: `chibchaweb.dominio.migracion`

Creador concreto que instancia registros ClienteLegado.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `tipo` | `+` | `—` | `String` | Devuelve "CLIENTE". |
| `crearRegistro` | `+` | `datos: String` | `RegistroLegado` | Instancia un ClienteLegado. |

### `CreadorHostingLegado` — hereda de `CreadorRegistroLegado`
Módulo Python: `chibchaweb.dominio.migracion`

Creador concreto que instancia registros HostingLegado.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `tipo` | `+` | `—` | `String` | Devuelve "HOSTING". |
| `crearRegistro` | `+` | `datos: String` | `RegistroLegado` | Instancia un HostingLegado. |

### `CreadorPagoLegado` — hereda de `CreadorRegistroLegado`
Módulo Python: `chibchaweb.dominio.migracion`

Creador concreto que instancia registros PagoLegado.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `tipo` | `+` | `—` | `String` | Devuelve "PAGO". |
| `crearRegistro` | `+` | `datos: String` | `RegistroLegado` | Instancia un PagoLegado. |

### `EstadoMigracion` — «enumeration»
Módulo Python: `chibchaweb.dominio.migracion`

Enumeración de los estados del proceso de migración.

| Literal | Descripción |
|---|---|
| `CREADA` | Proceso creado. |
| `SIMULADA` | Simulación completada con log. |
| `APROBADA` | El administrador aprobó el log. |
| `EJECUTADA` | Migración real completada. |
| `REVERTIDA` | La escritura real falló y se revirtió. |
| `CANCELADA` | El administrador canceló el proceso. |

### `NivelLog` — «enumeration»
Módulo Python: `chibchaweb.dominio.migracion`

Enumeración de la severidad de una entrada del log de migración.

| Literal | Descripción |
|---|---|
| `INFO` | Mensaje informativo. |
| `ADVERTENCIA` | Dato incompleto que no impide migrar. |
| `ERROR` | Registro inválido que no se migrará. |

## Capa de dominio — Integraciones Externas

### `ProveedorAutenticacion` — «interface»
Módulo Python: `chibchaweb.dominio.integraciones`

Interfaz que el dominio define para verificar la identidad de un usuario con un proveedor externo OAuth 2.0 (patrón Adapter).

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `autorizar` | `+` | `codigo: String` | `IdentidadExterna` | Cambia el código de autorización por la identidad verificada. |

### `IdentidadExterna`
Módulo Python: `chibchaweb.dominio.integraciones`

Datos verificados que entrega el proveedor de autenticación tras autorizar a un usuario. Objeto transitorio, no persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `identificadorExterno` | `-` | `String` | Identificador estable (sub) en el proveedor. | Cadena no vacía |
| `nombre` | `-` | `String` | Nombre verificado. | Cadena |
| `correo` | `-` | `String` | Correo verificado o declarado. | Correo válido |
| `correoVerificado` | `-` | `Boolean` | Indica si el proveedor verificó el correo. | true / false |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `puedePrellenarRegistro` | `+` | `—` | `Boolean` | Indica si el correo está verificado, condición para bloquear nombre y correo en el registro. |

### `ValidadorMedioPago` — «interface»
Módulo Python: `chibchaweb.dominio.integraciones`

Interfaz que el dominio define para verificar un medio de pago con un servicio externo (patrón Adapter).

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `verificar` | `+` | `medio: MedioPago` | `Boolean` | Verifica externamente el medio de pago. |

### `PasarelaPago` — «interface»
Módulo Python: `chibchaweb.dominio.integraciones`

Interfaz que el dominio define para ejecutar un cobro ante el procesador de pagos de las franquicias (patrón Adapter).

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `cobrar` | `+` | `medio: MedioPago, monto: Decimal` | `String` | Ejecuta el cargo y devuelve la referencia; vacía si fue rechazado. |

### `RegistradorDominio` — «interface»
Módulo Python: `chibchaweb.dominio.integraciones`

Interfaz que el dominio define para enviar solicitudes de dominio a un registrador externo (patrón Adapter).

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `enviar` | `+` | `documento: String` | `void` | Envía el documento al registrador; lanza una excepción ante falla de red. |

### `FuenteLegada` — «interface»
Módulo Python: `chibchaweb.dominio.integraciones`

Interfaz que el dominio define para leer los registros del sistema legado (patrón Adapter).

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `leerRegistros` | `+` | `—` | `String [0..*]` | Lee los registros crudos del sistema legado. |

## Capa de dominio — Respaldo y Contingencia

### `GestorContingencia`
Módulo Python: `chibchaweb.dominio.respaldo`

Coordina el respaldo en archivo plano cifrado cuando la base de datos no está disponible (RT04). Usa dos estrategias intercambiables: el algoritmo de cifrado y el medio de respaldo.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `algoritmos` | `-` | `AlgoritmoCifrado [1..*]` | Estrategias de cifrado disponibles (rol algoritmos). | Al menos una; cuatro en la configuración |
| `algoritmoActivo` | `-` | `String` | Nombre del algoritmo en uso. | AES, ChaCha20, Camellia o Twofish |
| `medio` | `-` | `MedioRespaldo` | Medio de respaldo en uso (rol medio). | Referencia obligatoria |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `cambiarAlgoritmo` | `+` | `nombre: String` | `void` | Activa uno de los algoritmos disponibles en tiempo de ejecución. |
| `cambiarMedio` | `+` | `medio: MedioRespaldo` | `void` | Cambia el medio de respaldo. |
| `respaldar` | `+` | `tipoEvento: String, contenido: String` | `void` | Cifra el contenido con el algoritmo activo y escribe en el medio el algoritmo, el tipo de evento y el contenido cifrado. |
| `recuperarPendientes` | `+` | `—` | `String [0..*]` | Lee los registros y descifra cada uno con el algoritmo que indica. |
| `confirmarSincronizacion` | `+` | `—` | `void` | Vacía el medio una vez sincronizado. |

### `AlgoritmoCifrado` — «interface»
Módulo Python: `chibchaweb.dominio.respaldo`

Interfaz de la estrategia de cifrado; el algoritmo activo se elige en tiempo de ejecución (patrón Strategy).

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `nombre` | `+` | `—` | `String` | Devuelve el nombre del algoritmo. |
| `cifrar` | `+` | `contenido: String` | `String` | Cifra el contenido. |
| `descifrar` | `+` | `contenido: String` | `String` | Descifra el contenido. |

### `CifradoAES` — implementa `AlgoritmoCifrado`
Módulo Python: `chibchaweb.dominio.respaldo`

Estrategia de cifrado con AES.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `nombre` | `+` | `—` | `String` | Devuelve "AES". |
| `cifrar` | `+` | `contenido: String` | `String` | Cifra con AES. |
| `descifrar` | `+` | `contenido: String` | `String` | Descifra con AES. |

### `CifradoChaCha20` — implementa `AlgoritmoCifrado`
Módulo Python: `chibchaweb.dominio.respaldo`

Estrategia de cifrado con ChaCha20.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `nombre` | `+` | `—` | `String` | Devuelve "ChaCha20". |
| `cifrar` | `+` | `contenido: String` | `String` | Cifra con ChaCha20. |
| `descifrar` | `+` | `contenido: String` | `String` | Descifra con ChaCha20. |

### `CifradoCamellia` — implementa `AlgoritmoCifrado`
Módulo Python: `chibchaweb.dominio.respaldo`

Estrategia de cifrado con Camellia.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `nombre` | `+` | `—` | `String` | Devuelve "Camellia". |
| `cifrar` | `+` | `contenido: String` | `String` | Cifra con Camellia. |
| `descifrar` | `+` | `contenido: String` | `String` | Descifra con Camellia. |

### `CifradoTwofish` — implementa `AlgoritmoCifrado`
Módulo Python: `chibchaweb.dominio.respaldo`

Estrategia de cifrado con Twofish.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `nombre` | `+` | `—` | `String` | Devuelve "Twofish". |
| `cifrar` | `+` | `contenido: String` | `String` | Cifra con Twofish. |
| `descifrar` | `+` | `contenido: String` | `String` | Descifra con Twofish. |

### `MedioRespaldo` — «interface»
Módulo Python: `chibchaweb.dominio.respaldo`

Interfaz de la estrategia de almacenamiento de contingencia (patrón Strategy).

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `escribir` | `+` | `registro: String` | `void` | Escribe un registro. |
| `leerPendientes` | `+` | `—` | `String [0..*]` | Lee los registros pendientes. |
| `disponible` | `+` | `—` | `Boolean` | Indica si el medio puede escribirse. |
| `limpiar` | `+` | `—` | `void` | Elimina los registros sincronizados. |

### `ArchivoPlano` — implementa `MedioRespaldo`
Módulo Python: `chibchaweb.dominio.respaldo`

Medio de respaldo que escribe los eventos cifrados en un archivo plano sobre almacenamiento persistente.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `ruta` | `-` | `String` | Ruta del archivo en el volumen persistente. | Ruta válida con permisos de escritura |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `escribir` | `+` | `registro: String` | `void` | Agrega una línea al archivo. |
| `leerPendientes` | `+` | `—` | `String [0..*]` | Lee las líneas del archivo. |
| `disponible` | `+` | `—` | `Boolean` | Indica si el archivo es escribible. |
| `limpiar` | `+` | `—` | `void` | Vacía el archivo. |

## Capa de dominio — Repositorios (corrección de capas)

### `RepositorioUsuario` — «interface»
Módulo Python: `chibchaweb.dominio.repositorios`

Interfaz del dominio para guardar y recuperar el agregado Usuario. La implementa MapeadorUsuario.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: Usuario` | `Integer` | Inserta el usuario en usuario y en la tabla de su subtipo, con direcciones, medio de pago y cuenta. |
| `actualizar` | `+` | `objeto: Usuario` | `void` | Actualiza el agregado Usuario. |
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

### `RepositorioSuscripcion` — «interface»
Módulo Python: `chibchaweb.dominio.repositorios`

Interfaz del dominio para el agregado Suscripcion (con sitio y pagos). La implementa MapeadorSuscripcion.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: Suscripcion` | `Integer` | Inserta el agregado Suscripcion y devuelve su id. |
| `actualizar` | `+` | `objeto: Suscripcion` | `void` | Actualiza el agregado Suscripcion. |
| `buscarPorId` | `+` | `id: Integer` | `Suscripcion` | Reconstruye el agregado Suscripcion por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `Suscripcion [0..*]` | Lista los Suscripcion que coinciden con el filtro. |
| `buscarVencidas` | `+` | `fecha: Date` | `Suscripcion [0..*]` | Lista las suscripciones activas con corte vencido. |
| `registrarPago` | `+` | `pago: Pago` | `void` | Inserta un pago. |
| `buscarPagosParaComision` | `+` | `distribuidor: Distribuidor, inicio: Date, fin: Date` | `Pago [0..*]` | Lista los pagos disponibles de los referidos del distribuidor en el periodo. |
| `buscarSitio` | `+` | `id: Integer` | `SitioWeb` | Reconstruye un sitio web por su id. |
| `restaurar` | `+` | `contenido: String` | `void` | Reinserta un agregado desde su contenido respaldado en contingencia (lo usa ServicioContingencia). **(agregado en implementación, P-05)** |

### `RepositorioComision` — «interface»
Módulo Python: `chibchaweb.dominio.repositorios`

Interfaz del dominio para el agregado Comision (con cheque). La implementa MapeadorComision.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: Comision` | `Integer` | Inserta el agregado Comision y devuelve su id. |
| `actualizar` | `+` | `objeto: Comision` | `void` | Actualiza el agregado Comision. |
| `buscarPorId` | `+` | `id: Integer` | `Comision` | Reconstruye el agregado Comision por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `Comision [0..*]` | Lista los Comision que coinciden con el filtro. |
| `registrarCheque` | `+` | `comision: Comision` | `void` | Inserta el cheque de la comisión. |
| `restaurar` | `+` | `contenido: String` | `void` | Reinserta un agregado desde su contenido respaldado en contingencia (lo usa ServicioContingencia). **(agregado en implementación, P-05)** |

### `RepositorioSolicitudDominio` — «interface»
Módulo Python: `chibchaweb.dominio.repositorios`

Interfaz del dominio para SolicitudDominio. La implementa MapeadorSolicitudDominio.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: SolicitudDominio` | `Integer` | Inserta el agregado SolicitudDominio y devuelve su id. |
| `actualizar` | `+` | `objeto: SolicitudDominio` | `void` | Actualiza el agregado SolicitudDominio. |
| `buscarPorId` | `+` | `id: Integer` | `SolicitudDominio` | Reconstruye el agregado SolicitudDominio por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `SolicitudDominio [0..*]` | Lista los SolicitudDominio que coinciden con el filtro. |
| `buscarPorSolicitante` | `+` | `idCliente: Integer` | `SolicitudDominio [0..*]` | Lista las solicitudes de un cliente. |
| `restaurar` | `+` | `contenido: String` | `void` | Reinserta un agregado desde su contenido respaldado en contingencia (lo usa ServicioContingencia). **(agregado en implementación, P-05)** |

### `RepositorioTicket` — «interface»
Módulo Python: `chibchaweb.dominio.repositorios`

Interfaz del dominio para el agregado Ticket (con movimientos). La implementa MapeadorTicket.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: Ticket` | `Integer` | Inserta el agregado Ticket y devuelve su id. |
| `actualizar` | `+` | `objeto: Ticket` | `void` | Actualiza el agregado Ticket. |
| `buscarPorId` | `+` | `id: Integer` | `Ticket` | Reconstruye el agregado Ticket por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `Ticket [0..*]` | Lista los Ticket que coinciden con el filtro. |
| `buscarCreadosEl` | `+` | `fecha: Date` | `Ticket [0..*]` | Lista los tickets creados en la fecha. |
| `buscarAbiertos` | `+` | `—` | `Ticket [0..*]` | Lista los tickets no resueltos. |
| `buscarPorReportante` | `+` | `idUsuario: Integer` | `Ticket [0..*]` | Lista los tickets de un usuario. |

### `RepositorioMigracion` — «interface»
Módulo Python: `chibchaweb.dominio.repositorios`

Interfaz del dominio para el agregado ProcesoMigracion (con log). La implementa MapeadorMigracion.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `insertar` | `+` | `objeto: ProcesoMigracion` | `Integer` | Inserta el agregado ProcesoMigracion y devuelve su id. |
| `actualizar` | `+` | `objeto: ProcesoMigracion` | `void` | Actualiza el agregado ProcesoMigracion. |
| `buscarPorId` | `+` | `id: Integer` | `ProcesoMigracion` | Reconstruye el agregado ProcesoMigracion por su id. |
| `buscarPorFiltro` | `+` | `filtro: String` | `ProcesoMigracion [0..*]` | Lista los ProcesoMigracion que coinciden con el filtro. |

### `RepositorioCatalogo` — «interface»
Módulo Python: `chibchaweb.dominio.repositorios`

Interfaz del dominio de solo lectura para los catálogos. La implementa MapeadorCatalogo.

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

### `UnidadDeTrabajo` — «interface»
Módulo Python: `chibchaweb.dominio.repositorios`

Interfaz del dominio para agrupar escrituras en una transacción (todo o nada). La implementa la persistencia; la usa ServicioMigracion en la ejecución real.

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `iniciar` | `+` | `—` | `void` | Abre la transacción. |
| `confirmar` | `+` | `—` | `void` | Confirma la transacción. |
| `revertir` | `+` | `—` | `void` | Revierte la transacción. |
