# Casos de uso comprometidos (25)

Este es el alcance firmado en el *Acta de compromiso de alcance del prototipo*. Cada CU indica el método de servicio, el endpoint (`api.md`) y la pantalla (`ui.md`).

Actores: **Visitante** (todavía sin registrar), **Cliente**, **Empleado de gestión** (rol Gestión), **Empleado de soporte** (rol Soporte), **Administrador** (rol Administrador), **Tiempo** (tarea programada) y los sistemas externos (proveedor OAuth, pasarela/validador de pagos, registrador de dominios, sistema legado).

## Resumen

| CU | Nombre | Actor | Método de servicio | Endpoint | Pantalla |
|---|---|---|---|---|---|
| CU-AUTH-01 | Acceder | Visitante | — (inicia el flujo) | `GET /auth/oauth/inicio` | M-01 |
| CU-AUTH-02 | Iniciar sesión | Visitante | `ServicioAcceso.iniciarSesion` | `POST /auth/oauth/callback` | M-01 → inicio por rol |
| CU-AUTH-03 | Registrarse | Visitante | `ServicioAcceso.registrarse` (+ `consultarPaquetes`, `consultarPlanes`) | `POST /auth/registro` | M-02, M-03, M-04 |
| CU-CLI-01 | Gestionar perfil | Cliente | `ServicioConsultas.consultarDetalle(CLIENTE, idSesion)` | `GET /clientes/me` | M-06 |
| CU-CLI-02 | Eliminar perfil | Cliente | `ServicioClientes.eliminarPerfil` | `DELETE /clientes/me` | M-08 |
| CU-CLI-03 | Modificar perfil | Cliente | `ServicioClientes.modificarPerfil` | `PATCH /clientes/me?categoria=` | M-07 |
| CU-EMP-01 | Gestionar empleado | Gestión | `ServicioConsultas.consultarBasico(EMPLEADO)` | `GET /empleados` | M-12 |
| CU-EMP-02 | Crear empleado | Gestión | `ServicioEmpleados.crearEmpleado` | `POST /empleados` | M-13 |
| CU-EMP-03 | Modificar empleado | Gestión | `ServicioEmpleados.modificarEmpleado` | `PUT /empleados/{id}` | M-13 |
| CU-EMP-04 | Eliminar empleado | Gestión | `ServicioEmpleados.eliminarEmpleado` | `DELETE /empleados/{id}` | M-12/M-14 + confirmación |
| CU-DIS-01 | Gestionar distribuidor | Gestión | `ServicioConsultas.consultarBasico(DISTRIBUIDOR)` | `GET /distribuidores` | M-15 |
| CU-DIS-02 | Crear distribuidor | Gestión | `ServicioDistribuidores.crearDistribuidor` | `POST /distribuidores` | M-13 (modo distribuidor) |
| CU-DIS-03 | Modificar distribuidor | Gestión | `ServicioDistribuidores.modificarDistribuidor` | `PUT /distribuidores/{id}` | M-13 |
| CU-DIS-04 | Eliminar distribuidor | Gestión | `ServicioDistribuidores.eliminarDistribuidor` | `DELETE /distribuidores/{id}` | M-15 + confirmación |
| CU-CON-01 | Consultar básico | Gestión, Soporte | `ServicioConsultas.consultarBasico` | `GET /consultas/{tipoEntidad}?filtro=` | M-12, M-15, M-16, M-17 |
| CU-CON-02 | Consultar detalle | Gestión, Soporte | `ServicioConsultas.consultarDetalle` | `GET /consultas/{tipoEntidad}/{id}` | M-14, detalle en M-16 y M-17 |
| CU-FAC-01 | Cargar pago | Tiempo | `ServicioFacturacion.cargarPago` | comando `cargar_pagos` | — |
| CU-DOM-01 | Registrar solicitud de dominio | Cliente | `ServicioDominios.registrarSolicitudDominio` | `POST /dominios/solicitudes` | M-09 |
| CU-DOM-02 | Generar y enviar solicitud XML | (incluido en DOM-01) | `ServicioDominios.generarYEnviarSolicitudXML` | mismo POST | M-09 |
| CU-COM-01 | Calcular comisión | Tiempo | `ServicioComisiones.calcularComision` | comando `calcular_comisiones` | — |
| CU-COM-02 | Generar cheque | Tiempo | `ServicioComisiones.generarCheque` | comando `generar_cheques` | — |
| CU-SOP-01 | Registrar ticket | Cliente, cualquier empleado | `ServicioSoporte.registrarTicket` | `POST /tickets` | M-10 |
| CU-SOP-02 | Consultar tickets diario | Soporte | `ServicioSoporte.consultarTicketsDiario` | `GET /tickets/diarios?fecha=` | M-17 |
| CU-SOP-03 | Enrutar por nivel de servicio | Soporte | `ServicioSoporte.enrutarPorNivelServicio` | `POST /tickets/{id}/enrutamiento` | M-17 (detalle) |
| CU-MIG-01 | Migrar registros legados | Administrador | `ServicioMigracion.migrarRegistrosLegados`, `confirmarMigracion`, `cancelarMigracion` | `POST /migraciones`, `/migraciones/{id}/confirmacion`, `/cancelacion` | M-19 |

Requerimientos técnicos:

| RT | Qué | Dónde se ve |
|---|---|---|
| RT01–RT03 | Calidad, nombrado y patrones (capas, Strategy, Adapter, Builder, Factory Method, Data Mapper, Layer Supertype, Repository) | revisión de `revisor-arquitectura`, `lint-imports` |
| RT04 | Contingencia: respaldo cifrado en archivo plano con algoritmo seleccionable en ejecución, y sincronización | `ServicioContingencia`, `GestorContingencia`, M-20, `/contingencia/*` |

Operaciones de apoyo que **no** son CU pero se necesitan: `consultarPaquetes`, `consultarPlanes`, `consultarRoles`, `consultarSolicitudes`, `consultarMisTickets`, `consultarSitios`, `consultarRespaldoPendiente` y el cierre de sesión.

---

## Flujos

Formato: **Pre** precondición · **FP** flujo principal · **FA** flujos alternos · **Post** resultado.

### CU-AUTH-01 Acceder
- **FP:** 1. El visitante abre `/`. 2. Se muestra M-01 con *Iniciar sesión con proveedor externo* y *Crear una cuenta*. 3. Cualquiera de las dos pide `GET /auth/oauth/inicio` y redirige al proveedor (crear cuenta también requiere autenticarse primero).
- **FA:** si ya hay sesión válida (`GET /auth/sesion` = 200), se va directo al inicio del rol.

### CU-AUTH-02 Iniciar sesión
- **FP:** 1. El proveedor redirige a `/auth/callback`. 2. El frontend manda el código. 3. `iniciarSesion(codigo)`: `proveedor.autorizar(codigo)` → `IdentidadExterna`; `usuarios.buscarPorIdentificadorExterno(sub)`; si se encuentra, `cuenta.registrarAcceso()` y se devuelve `ResultadoAccesoDTO(registrado=true, tipoUsuario, rol, operaciones)`. 4. El frontend redirige según el rol: Cliente → M-05, Gestión → M-11, Soporte → M-17, Administrador → M-18.
- **FA1 (RN-07):** no se encuentra por `sub` y `correoVerificado`: `buscarPorCorreo`; si existe y es autenticable, `vincularCuenta(identidad)` y sigue en el paso 3.
- **FA2:** no existe → `registrado=false` con `nombre` y `correo`. El frontend va a M-02 con esos datos ya llenos.
- **FA3:** usuario inactivo → 403 `USUARIO_INACTIVO`. Código inválido o `state` distinto → 401 `AUTORIZACION_FALLIDA`.

### CU-AUTH-03 Registrarse
- **Pre:** hay una identidad pendiente en la sesión (FA2 de AUTH-02).
- **FP:** M-02 teléfono, dirección de residencia, nombre del sitio y plataforma → M-03 paquete y plan (con el monto calculado en vivo) → M-04 dirección de facturación, tarjeta, código de distribuidor opcional → *Crear cuenta*. `registrarse(datos)`: crea las `Direccion`, la `TarjetaCredito` (con su `Franquicia` del catálogo), el `Cliente`, el `SitioWeb` y la `Suscripcion`; `cliente.validarDatosFacturacion(validador)`; asocia el distribuidor (RN-13); `usuarios.insertar(cliente)`; `suscripciones.insertar(suscripcion)`; `cliente.vincularCuenta(identidad)`. Devuelve el id. El backend abre la sesión y el frontend va a M-05.
- **FA:** validación fallida → 422 con `campo`, y el frontend vuelve al paso donde está ese campo. Subdominio ocupado → 409 `SUBDOMINIO_EN_USO`. Cancelar → se borra la identidad pendiente y se vuelve a M-01.

### CU-CLI-01 Gestionar perfil
- **FP:** M-06 muestra los datos personales, el sitio, el paquete y plan, la dirección y la tarjeta enmascarada, con los botones *Modificar* (CLI-03) y *Eliminar* (CLI-02).

### CU-CLI-02 Eliminar perfil
- **FP:** M-08 pide confirmación. `eliminarPerfil(idCliente)` → `inactivar()` + suspende las suscripciones (RN-09). Se cierra la sesión y se va a M-01.

### CU-CLI-03 Modificar perfil
- **FP:** M-07 tiene tres pestañas y cada una corresponde a una `CategoriaPerfil`. `PERSONAL`: nombre, teléfono, dirección de residencia, sitio y plataforma. `PAQUETE_PLAN`: cambia el paquete y/o el plan de `idSuscripcion` (`cambiarPaquete`/`cambiarPlan`; aplica desde el próximo corte). `PAGO`: dirección de facturación y tarjeta, vuelve a validar con RN-10. *Guardar* manda solo el bloque de la pestaña activa.
- **FA:** validación → 422. El correo no se puede editar (RN-05).

### CU-EMP-01..04 Gestionar / crear / modificar / eliminar empleado
- **FP:** M-12 lista con búsqueda (`consultarBasico(EMPLEADO, filtro)`) → *Crear* o *Editar* abren M-13 (nombre, documento, correo, teléfono, cargo de `consultarRoles`) → *Guardar*. *Ver* abre M-14 (`consultarDetalle`). *Eliminar* pide confirmación → `eliminarEmpleado` (baja lógica).
- **Reglas:** correo y documento únicos (409 `DUPLICADO` con el `campo`). El empleado entra después con su cuenta externa usando ese correo (RN-07).

### CU-DIS-01..04 Gestionar / crear / modificar / eliminar distribuidor
- Igual que los empleados, sin cargo. Al crear se genera el código (RN-15), que aparece en el listado y en el detalle. El distribuidor **no** inicia sesión.

### CU-CON-01 Consultar básico · CU-CON-02 Consultar detalle
- **FP:** `consultarBasico(tipoEntidad, filtro)` → `ResumenDTO[]` (id, titulo, subtitulo, estado). El filtro busca sin distinguir mayúsculas en nombre, correo o documento (en tickets, en descripción o id). `consultarDetalle(tipoEntidad, id)` → `DetalleDTO` con `campos` como lista de pares `"Etiqueta: valor"`.
- **Permisos:** CLIENTE, EMPLEADO y DISTRIBUIDOR → `CONSULTAR_REGISTROS` (Gestión). TICKET → `ATENDER_TICKETS` (Soporte). El cliente solo puede ver su propio detalle por `/clientes/me`.

### CU-FAC-01 Cargar pago
- **Disparo:** `python manage.py cargar_pagos [--fecha AAAA-MM-DD]` (cron diario a las 02:00 en Docker).
- **FP:** `cargarPago(fechaCorte)` → `suscripciones.buscarVencidas(fecha)`; para cada una, `s.cobrar(pasarela)` y `suscripciones.registrarPago(...)`/`actualizar`. Devuelve cuántos cobros procesó (exitosos y fallidos). Ver RN-01..03.

### CU-DOM-01 Registrar solicitud · CU-DOM-02 Generar y enviar XML
- **FP:** M-09: nombre + extensión → `registrarSolicitudDominio(idCliente, nombre, extension)` (valida con RN-16 y queda `REGISTRADA`) → la vista llama enseguida `generarYEnviarSolicitudXML(id)`: `construirDocumento(ConstructorXML())` → `enviarA(registrador, documento)` → `ENVIADA` o `FALLIDA`. La respuesta trae el estado. Abajo se ve la tabla de `consultarSolicitudes`.
- **FA:** formato inválido → 422 (no se guarda). Registrador caído → la solicitud queda `FALLIDA` y la respuesta es 201 con ese estado; el cliente puede enviar una solicitud nueva.

### CU-COM-01 Calcular comisión · CU-COM-02 Generar cheque
- **Disparo:** `calcular_comisiones --inicio --fin` (el primer día de cada mes, para el mes anterior) y luego `generar_cheques` (emite el cheque de cada comisión que no lo tiene, ver P-08).
- **FP:** RN-19..21.

### CU-SOP-01 Registrar ticket
- **FP:** M-10: categoría, descripción y sitio afectado (opcional; solo clientes, de `consultarSitios`) → `registrarTicket(idUsuario, categoria, descripcion, idSitio)` → `ABIERTO` en el nivel 1. Abajo se ve la tabla de `consultarMisTickets`.

### CU-SOP-02 Consultar tickets diario
- **FP:** M-17 bandeja con selector de fecha (por defecto hoy) → `consultarTicketsDiario(fecha)` (RN-24).

### CU-SOP-03 Enrutar por nivel de servicio
- **FP:** en el detalle del ticket (M-17), observación + *Marcar resuelto* (`escalar=false`) o *Escalar de nivel* (`escalar=true`) → `enrutarPorNivelServicio(...)` (RN-23).
- **FA:** último nivel o ticket resuelto → 409 `ESTADO_INVALIDO`. Sin observación → 422.

### CU-MIG-01 Migrar registros legados
- **FP (fase 1):** M-19 *Ejecutar simulación* → `migrarRegistrosLegados(idEjecutor)` → `ResultadoMigracionDTO` (válidos, inválidos y log). **Fase 2:** el administrador revisa el log → *Ejecutar migración real* → `confirmarMigracion(idProceso)` → `EJECUTADA` o `REVERTIDA` (RN-27). *Cancelar* → `cancelarMigracion` → `CANCELADA`.
- **FA:** confirmar sin haber simulado o dos veces → 409 `ESTADO_INVALIDO`.

### RT04 Contingencia
- M-20: selector de algoritmo + *Aplicar* → `cambiarAlgoritmoCifrado(nombre)`. Tabla de eventos pendientes (`consultarRespaldoPendiente`) + *Sincronizar* → `sincronizarRespaldo()` (RN-29, RN-30). Mientras haya contingencia, cualquier escritura de los 4 agregados que respaldan devuelve 503 `CONTINGENCIA` y deja el evento en el respaldo.
