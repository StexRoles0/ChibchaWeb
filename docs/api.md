# Contrato REST (v1)

Base: `/api/v1`. El formato es JSON con claves en `camelCase`. Las fechas van como `AAAA-MM-DD` y las fechas-hora en ISO 8601 con zona. Los montos van como **string decimal** (`"54.00"`) para no perder precisión.
La autenticación usa la cookie de sesión de Django y CSRF (encabezado `X-CSRFToken`, que Angular manda automáticamente con `withXsrfConfiguration({cookieName:'csrftoken', headerName:'X-CSRFToken'})`).

Este contrato es la frontera entre `backend-dev` y `frontend-dev`. Si cambia, se cambia aquí primero y se anota en `decisiones.md`.

## Errores

Todos los errores usan el mismo cuerpo:

```json
{ "codigo": "VALIDACION", "mensaje": "La tarjeta está vencida", "campo": "vencimiento" }
```

| HTTP | `codigo` | Excepción del dominio o servicio |
|---|---|---|
| 400 | `SOLICITUD_INVALIDA` | JSON mal formado o tipos incorrectos (serializer) |
| 401 | `NO_AUTENTICADO` / `AUTORIZACION_FALLIDA` | sin sesión / OAuth falló |
| 403 | `SIN_PERMISO` / `USUARIO_INACTIVO` | falta la operación / baja lógica |
| 404 | `NO_ENCONTRADO` | `NoEncontradoError` |
| 409 | `DUPLICADO` / `ESTADO_INVALIDO` / `SUBDOMINIO_EN_USO` | `DuplicadoError` / `EstadoInvalidoError` |
| 422 | `VALIDACION` (con `campo`) / `REGLA_NEGOCIO` | `ValidacionError` / `ReglaNegocioError` |
| 503 | `CONTINGENCIA` | `ContingenciaActivaError`: la BD no está disponible y el evento quedó respaldado |

## DTO (iguales a DC-SRV-01)

```ts
interface ResultadoAccesoDTO { registrado: boolean; idUsuario?: number; nombre: string; correo: string;
  tipoUsuario: 'CLIENTE'|'EMPLEADO'|''; rol?: 'Gestión'|'Soporte'|'Administrador'; operaciones: string[]; }
interface DatosClienteDTO { telefono: string; lineaResidencia: string; ciudadResidencia: string; codigoPostalResidencia: string;
  sitio: string; plataforma: 'WINDOWS'|'UNIX'; idPaquete: number; idPlan: number;
  lineaFacturacion: string; ciudadFacturacion: string; codigoPostalFacturacion: string;
  numeroTarjeta: string; vencimiento: string /* AAAA-MM-01 */; codigoSeguridad: string; franquicia: 'VISA'|'MASTERCARD'|'DINERS';
  codigoDistribuidor?: string; idSuscripcion?: number; nombre?: string /* solo PATCH PERSONAL y registro */ }
interface EmpleadoDTO { nombre: string; documento: string; correo: string; telefono: string; idRol: number; }
interface DistribuidorDTO { nombre: string; documento: string; correo: string; telefono: string; }
interface ResumenDTO { id: number; titulo: string; subtitulo: string; estado: string; }
interface DetalleDTO { id: number; titulo: string; campos: string[]; }   // cada campo: "clave: valor"
interface ResultadoMigracionDTO { idProceso: number; validos: number; invalidos: number; entradas: string[]; } // "NIVEL|tipo|idLegado|mensaje"
```

`identificadorExterno` y `correo` del registro **no** vienen en el cuerpo: la vista los toma de la identidad pendiente que está en la sesión (ver P-07).

`DetalleDTO.campos` usa claves fijas por tipo para que el frontend pueda llenar formularios:
- **CLIENTE:** `nombre, correo, telefono, lineaResidencia, ciudadResidencia, codigoPostalResidencia, lineaFacturacion, ciudadFacturacion, codigoPostalFacturacion, tarjeta (enmascarada), franquicia, vencimiento, idSuscripcion, sitio, plataforma, idPaquete, paquete, idPlan, plan, montoPeriodo, fechaCorte, distribuidor, activo`
- **EMPLEADO:** `nombre, documento, correo, telefono, idRol, rol, activo, fechaRegistro`
- **DISTRIBUIDOR:** `nombre, documento, correo, telefono, codigo, categoria, referidos, activo`
- **TICKET:** `categoria, estado, nivel, reportante, sitio, fechaCreacion, descripcion, movimiento` (se repite: `"movimiento: 2026-11-16 10:30|Ana Ruiz|ESCALADO|Gestión|observación"`)

## Endpoints

### Acceso — `ServicioAcceso`
| Verbo y ruta | Permiso | Cuerpo → respuesta | Servicio |
|---|---|---|---|
| `GET /auth/oauth/inicio[?correo=]` | público | → `{ url }` | — (vista: state + PKCE). Con `SIMULAR_EXTERNOS`, `correo` es obligatorio y la URL es `/auth/callback?code=dev:<correo>&state=…` |
| `POST /auth/oauth/callback` | público | `{ codigo, estado }` → `ResultadoAccesoDTO` | `iniciarSesion(codigo)` |
| `GET /auth/sesion` | autenticado | → `ResultadoAccesoDTO` (de la sesión) | — |
| `POST /auth/logout` | autenticado | → 204 | — |
| `GET /catalogo/paquetes` | público | → `ResumenDTO[]` (subtitulo = `"10.00"`) | `consultarPaquetes()` |
| `GET /catalogo/planes` | público | → `ResumenDTO[]` (subtitulo = `"3|0.05"`) | `consultarPlanes()` |
| `POST /auth/registro` | identidad pendiente | `DatosClienteDTO` → 201 `ResultadoAccesoDTO` | `registrarse(datos)` |

### Clientes — `ServicioClientes`
| Verbo y ruta | Permiso | Cuerpo → respuesta | Servicio |
|---|---|---|---|
| `GET /clientes/me` | `EsCliente` | → `DetalleDTO` | `ServicioConsultas.consultarDetalle(CLIENTE, idSesion)` |
| `PATCH /clientes/me?categoria=PERSONAL\|PAQUETE_PLAN\|PAGO` | `EsCliente` | `DatosClienteDTO` parcial → 204 | `modificarPerfil(idSesion, categoria, datos)` |
| `DELETE /clientes/me` | `EsCliente` | → 204 (cierra la sesión) | `eliminarPerfil(idSesion)` |
| `GET /clientes/me/sitios` | `EsCliente` | → `ResumenDTO[]` | `consultarSitios(idSesion)` (P-03) |

### Empleados y distribuidores
| Verbo y ruta | Permiso | Cuerpo → respuesta | Servicio |
|---|---|---|---|
| `GET /catalogo/roles` | `GESTIONAR_EMPLEADOS` | → `ResumenDTO[]` | `ServicioEmpleados.consultarRoles()` |
| `GET /empleados?filtro=` | `GESTIONAR_EMPLEADOS` | → `ResumenDTO[]` | `ServicioConsultas.consultarBasico(EMPLEADO, filtro)` |
| `GET /empleados/{id}` | `GESTIONAR_EMPLEADOS` | → `DetalleDTO` | `consultarDetalle(EMPLEADO, id)` |
| `POST /empleados` | `GESTIONAR_EMPLEADOS` | `EmpleadoDTO` → 201 `{ id }` | `crearEmpleado(datos)` |
| `PUT /empleados/{id}` | `GESTIONAR_EMPLEADOS` | `EmpleadoDTO` → 204 | `modificarEmpleado(id, datos)` |
| `DELETE /empleados/{id}` | `GESTIONAR_EMPLEADOS` | → 204 | `eliminarEmpleado(id)` |
| `GET\|POST /distribuidores`, `GET\|PUT\|DELETE /distribuidores/{id}` | `GESTIONAR_DISTRIBUIDORES` | igual, con `DistribuidorDTO`; el POST devuelve `{ id, codigo }` | `ServicioDistribuidores.*` |

### Consultas — `ServicioConsultas`
| Verbo y ruta | Permiso | Respuesta | Servicio |
|---|---|---|---|
| `GET /consultas/{tipoEntidad}?filtro=` | CLIENTE/EMPLEADO/DISTRIBUIDOR: `CONSULTAR_REGISTROS`; TICKET: `ATENDER_TICKETS` | `ResumenDTO[]` | `consultarBasico(tipoEntidad, filtro)` |
| `GET /consultas/{tipoEntidad}/{id}` | ídem | `DetalleDTO` | `consultarDetalle(tipoEntidad, id)` |

`tipoEntidad` ∈ `CLIENTE | EMPLEADO | DISTRIBUIDOR | TICKET`. Las rutas `/empleados` y `/distribuidores` (GET) son atajos que llaman a los mismos métodos.

### Dominios — `ServicioDominios`
| Verbo y ruta | Permiso | Cuerpo → respuesta | Servicio |
|---|---|---|---|
| `POST /dominios/solicitudes` | `EsCliente` | `{ nombre, extension }` → 201 `{ id, estado }` | `registrarSolicitudDominio(...)` y luego `generarYEnviarSolicitudXML(id)` |
| `GET /dominios/solicitudes` | `EsCliente` | → `ResumenDTO[]` (titulo = nombre completo, estado) | `consultarSolicitudes(idSesion)` |

### Soporte — `ServicioSoporte`
| Verbo y ruta | Permiso | Cuerpo → respuesta | Servicio |
|---|---|---|---|
| `POST /tickets` | autenticado | `{ categoria, descripcion, idSitio? }` → 201 `{ id }` | `registrarTicket(idSesion, ...)` |
| `GET /tickets/mios` | autenticado | → `ResumenDTO[]` | `consultarMisTickets(idSesion)` |
| `GET /tickets/diarios?fecha=` | `ATENDER_TICKETS` | → `ResumenDTO[]` | `consultarTicketsDiario(fecha)` |
| `GET /tickets/{id}` | `ATENDER_TICKETS` | → `DetalleDTO` | `ServicioConsultas.consultarDetalle(TICKET, id)` |
| `POST /tickets/{id}/enrutamiento` | `ATENDER_TICKETS` | `{ escalar, observacion }` → 204 | `enrutarPorNivelServicio(id, idSesion, escalar, observacion)` |

### Migración — `ServicioMigracion`
| Verbo y ruta | Permiso | Respuesta | Servicio |
|---|---|---|---|
| `POST /migraciones` | `MIGRAR_DATOS` | 201 `ResultadoMigracionDTO` | `migrarRegistrosLegados(idSesion)` |
| `POST /migraciones/{id}/confirmacion` | `MIGRAR_DATOS` | `{ estado: 'EJECUTADA'\|'REVERTIDA' }` | `confirmarMigracion(id)` |
| `POST /migraciones/{id}/cancelacion` | `MIGRAR_DATOS` | `{ estado: 'CANCELADA' }` | `cancelarMigracion(id)` |

### Contingencia — `ServicioContingencia`
| Verbo y ruta | Permiso | Cuerpo → respuesta | Servicio |
|---|---|---|---|
| `GET /contingencia/pendientes` | `GESTIONAR_CONTINGENCIA` | → `ResumenDTO[]` (titulo = tipoEvento, subtitulo = algoritmo) | `consultarRespaldoPendiente()` (P-04) |
| `PUT /contingencia/algoritmo` | `GESTIONAR_CONTINGENCIA` | `{ nombre: 'AES'\|'ChaCha20'\|'Camellia'\|'Twofish' }` → 204 | `cambiarAlgoritmoCifrado(nombre)` |
| `POST /contingencia/sincronizacion` | `GESTIONAR_CONTINGENCIA` | → `{ sincronizados }` | `sincronizarRespaldo()` |

### Tareas programadas (management commands, no HTTP)
| Comando | Servicio | Programación en Docker |
|---|---|---|
| `cargar_pagos [--fecha]` | `ServicioFacturacion.cargarPago` | diario 02:00 |
| `calcular_comisiones [--inicio --fin]` | `ServicioComisiones.calcularComision` | día 1 de cada mes 03:00, mes anterior |
| `generar_cheques` | `ServicioComisiones.consultarComisionesSinCheque` + `generarCheque` | día 1 de cada mes 03:30 |

## Anexo: XML de solicitud de dominio (Builder)

`SolicitudDominio.construirDocumento(constructor)` (el director) llama en este orden: `iniciarDocumento()` → `agregarSolicitante(cliente)` → `agregarDominio(nombre, extension)` → `agregarFecha(fechaSolicitud)` → `obtenerResultado()`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<solicitudDominio>
  <solicitante><nombre>Laura Gómez</nombre><correo>laura@correo.co</correo></solicitante>
  <dominio><nombre>tiendalaura</nombre><extension>.co</extension></dominio>
  <fecha>2026-11-16T10:30:00-05:00</fecha>
</solicitudDominio>
```
