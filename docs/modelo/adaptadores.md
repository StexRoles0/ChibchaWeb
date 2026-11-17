# Adaptadores

Implementaciones de las interfaces de integración. Viven fuera del dominio y son las únicas clases que conocen las API externas.

> Convenciones: visibilidad `-` privada, `+` pública, `#` protegida. La multiplicidad acompaña al tipo (`[0..*]`, `[1..*]`, `[0..1]`). Getters/setters no se listan: existe uno por atributo privado salvo en colecciones, que se manipulan solo con los métodos listados. Las subclases listan solo lo propio y lo que sobrescriben. En Python los nombres se traducen a `snake_case` de forma mecánica (`validarDatosFacturacion` → `validar_datos_facturacion`); las clases conservan su nombre.

## Adaptadores

### `AdaptadorOAuth` — implementa `ProveedorAutenticacion`
Módulo Python: `chibchaweb.adaptadores`

Adaptador que traduce la API del proveedor OAuth 2.0 a la interfaz ProveedorAutenticacion: intercambia el código por los tokens y valida el ID token.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `urlProveedor` | `-` | `String` | URL base del proveedor OAuth. | URL HTTPS |
| `idAplicacion` | `-` | `String` | Identificador de la aplicación registrada en el proveedor. | Cadena no vacía |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `autorizar` | `+` | `codigo: String` | `IdentidadExterna` | Intercambia el código por los tokens, valida el ID token y construye la IdentidadExterna. |

### `AdaptadorValidadorTarjeta` — implementa `ValidadorMedioPago`
Módulo Python: `chibchaweb.adaptadores`

Adaptador del servicio externo de verificación de tarjetas a la interfaz ValidadorMedioPago.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `urlServicio` | `-` | `String` | URL del servicio de verificación. | URL HTTPS |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `verificar` | `+` | `medio: MedioPago` | `Boolean` | Traduce la tarjeta a la petición del servicio externo y devuelve su veredicto. |

### `AdaptadorProcesadorPagos` — implementa `PasarelaPago`
Módulo Python: `chibchaweb.adaptadores`

Adaptador del procesador de pagos de las franquicias a la interfaz PasarelaPago.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `urlProcesador` | `-` | `String` | URL del procesador de pagos. | URL HTTPS |
| `codigoComercio` | `-` | `String` | Código de comercio de ChibchaWEB. | Cadena no vacía |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `cobrar` | `+` | `medio: MedioPago, monto: Decimal` | `String` | Traduce el medio y el monto a la API del procesador y devuelve la referencia. |

### `AdaptadorRegistradorDominio` — implementa `RegistradorDominio`
Módulo Python: `chibchaweb.adaptadores`

Adaptador del registrador de dominios externo a la interfaz RegistradorDominio.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `urlRegistrador` | `-` | `String` | URL del servicio del registrador. | URL HTTPS |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `enviar` | `+` | `documento: String` | `void` | Transmite el XML al registrador. |

### `AdaptadorSistemaLegado` — implementa `FuenteLegada`
Módulo Python: `chibchaweb.adaptadores`

Adaptador del sistema legado a la interfaz FuenteLegada.

| Atributo | Vis. | Tipo | Descripción | Rango de valores |
|---|---|---|---|---|
| `origenDatos` | `-` | `String` | Ubicación o conexión del sistema legado. | Cadena no vacía |

| Método | Vis. | Parámetros | Retorno | Intencionalidad |
|---|---|---|---|---|
| `leerRegistros` | `+` | `—` | `String [0..*]` | Extrae los registros del legado como texto con su tipo. |
