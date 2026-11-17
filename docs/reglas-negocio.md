# Reglas de negocio

Todas estas reglas se implementan **en el dominio**, con pruebas unitarias. El código RN-xx sirve para citarlas en las pruebas y en los commits.

## Catálogos (datos fijos, `docs/schema.sql`)

| Paquete | Tarifa mensual (USD) |
|---|---|
| Chibcha-Plata | 5.00 |
| Chibcha-Oro | 10.00 |
| Chibcha-Platino | 20.00 |

| Plan | Meses | Descuento |
|---|---|---|
| Mensual | 1 | 0 % |
| Trimestral | 3 | 5 % |
| Semestral | 6 | 10 % |
| Anual | 12 | 15 % |

Franquicias admitidas: **VISA, MASTERCARD, DINERS**. El patrón de cada una está en la columna `franquicia.patron_numero`.
Niveles de servicio: **Soporte (1) → Gestión (2) → Desarrollo (3, último)**.
Roles de empleado: **Gestión, Soporte, Administrador**.
Extensiones de dominio admitidas: **.com, .co, .net, .org**.

## Facturación

- **RN-01** `monto del periodo = tarifaMensual × meses × (1 − descuento)`, redondeado a 2 decimales con `ROUND_HALF_UP` y usando `Decimal`, nunca `float`. Ejemplo: Oro + Semestral = 10 × 6 × 0,90 = **54.00**. Lo calcula `PaqueteHosting.calcularMonto(plan)` y lo llama `Suscripcion.montoDelPeriodo()`.
- **RN-02** Una suscripción está vencida si `fechaCorte ≤ fecha`. `cargarPago(fechaCorte)` cobra **todas** las suscripciones activas vencidas.
- **RN-03** `Suscripcion.cobrar(pasarela)` crea un `Pago`. Si sale bien queda `EXITOSO` con la `referenciaFranquicia` que devolvió la pasarela, y `avanzarCorte()` suma `plan.meses` a la fecha de corte. Si falla queda `FALLIDO`, sin referencia, y el corte no se mueve. Un pago fallido no detiene el lote.
- **RN-04** Al registrarse se crea la suscripción con `fechaInicio = hoy` y `fechaCorte = hoy`. El primer cobro lo hace la tarea programada del día.

## Cuentas y perfiles

- **RN-05** El correo del usuario es único. El cliente **no puede cambiar** el correo verificado que viene del proveedor (en M-07 el campo está bloqueado).
- **RN-06** `Usuario.vincularCuenta(identidad)` falla si el usuario no es autenticable (`Distribuidor.esAutenticable() = false`) o si ya tiene una cuenta.
- **RN-07** Primer ingreso de empleados y clientes migrados: si no se encuentra a nadie con el `sub` (`identificadorExterno`) y la identidad trae `correoVerificado = true`, se busca por correo con `buscarPorCorreo`, se vincula la cuenta y se entra. Si el correo no está verificado, no se vincula nada y se trata como un usuario sin registrar.
- **RN-08** El usuario se identifica siempre por `sub` y proveedor, nunca solo por el correo.
- **RN-09** Las bajas son lógicas. `Usuario.inactivar()` pone `activo = false`. Cuando el cliente elimina su perfil, también se suspenden sus suscripciones (`Cliente.cancelarSuscripcion` para cada una). Un usuario inactivo no puede iniciar sesión (403 `USUARIO_INACTIVO`).
- **RN-10** `Cliente.validarDatosFacturacion(validador)` valida las dos direcciones (`Direccion.validar()`: línea, ciudad y código postal no vacíos; código postal alfanumérico de 4 a 10 caracteres) y luego llama `medioPago.validar(validador)`. Se ejecuta antes de guardar en el registro y cada vez que se modifica la dirección o la tarjeta.
- **RN-11** `TarjetaCredito.validar(validador)` revisa, en este orden, que (a) el número cumpla el patrón de la franquicia elegida, (b) la tarjeta esté vigente (`vencimiento` ≥ primer día del mes actual), (c) el `codigoSeguridad` tenga exactamente 3 dígitos, y (d) `validador.verificar(this)` responda `true`. Si algo falla lanza `ValidacionError` con el campo que falló.
- **RN-12** El `codigoSeguridad` **nunca se guarda**. El número se guarda cifrado con el algoritmo activo, junto con el nombre del algoritmo y los últimos 4 dígitos. `descripcion()` devuelve el número enmascarado, por ejemplo `VISA •••• 4242`.
- **RN-13** El código de distribuidor en el registro es opcional. Si llega y no existe un distribuidor activo con ese código, es un error de validación (no se ignora). Si existe, se llama `Cliente.asociarDistribuidor(d)` y `d.agregarReferido(cliente)`.
- **RN-14** El sitio del registro se crea con `subdominio = <sitio>.chibchaweb.co` (único) y la plataforma elegida (`WINDOWS` o `UNIX`).
- **RN-15** El código del distribuidor lo genera el sistema con la forma `DIS-` + 6 caracteres alfanuméricos en mayúscula, y es único.

## Dominios

- **RN-16** `SolicitudDominio.validarFormato()`: el nombre tiene de 1 a 63 caracteres, solo letras, dígitos y guiones, sin guion al inicio ni al final; la extensión debe estar admitida. El nombre se guarda en minúsculas.
- **RN-17** Estados: `REGISTRADA → ENVIADA` (si el registrador responde bien, con `fechaEnvio`) o `REGISTRADA → FALLIDA`. Solo se puede enviar una solicitud pendiente (`estaPendiente()`).
- **RN-18** El XML se arma con el Builder (`ConstructorXML`). `SolicitudDominio.construirDocumento(constructor)` es el director. Formato en `api.md` §Anexo XML.

## Comisiones

- **RN-19** Categoría del distribuidor según la cantidad de referidos: **Básica** si son ≤ 100 (10 %), **Premium** si son ≥ 101 (15 %). La decide `Distribuidor.determinarCategoria(categorias)` recorriendo las estrategias.
- **RN-20** `calcularComision(inicio, fin)` crea una `Comision` por cada distribuidor que tenga pagos `EXITOSO`, sin comisionar, de clientes que él refirió y con fecha dentro de [inicio, fin]. `monto = Σ pagosBase × porcentaje`. Cada pago base queda `comisionado = true`. Si un distribuidor no tiene pagos, no se le crea comisión.
- **RN-21** `generarCheque(idComision)` falla si la comisión ya tiene cheque. Número de cheque: `CHQ-<año>-<id con 6 dígitos>`. Beneficiario: nombre y documento del distribuidor. `montoEnLetras()` en español (por ejemplo, "CINCUENTA Y CUATRO DÓLARES CON 00/100").

## Soporte

- **RN-22** Cualquier usuario autenticado (cliente o empleado) puede registrar un ticket. Este empieza `ABIERTO`, en el nivel de orden 1 (`buscarNivelInicial`). El sitio afectado es opcional y, si viene, tiene que ser de un sitio del cliente.
- **RN-23** Solo un empleado del rol Soporte (operación `ATENDER_TICKETS`) enruta. Si `escalar = true`, el ticket pasa al nivel siguiente y queda `ESCALADO`; falla si el ticket está `RESUELTO` o si el nivel es el último. Si `escalar = false`, queda `RESUELTO`. Cada cambio crea un `MovimientoTicket` con responsable, observación (obligatoria), estado y nivel resultantes.
- **RN-24** La bandeja diaria (`consultarTicketsDiario(fecha)`) muestra la unión de los tickets creados ese día y todos los que siguen abiertos (`ABIERTO` o `ESCALADO`), sin repetir, del más reciente al más antiguo.

## Migración

- **RN-25** Estados: `CREADA → SIMULADA → APROBADA → EJECUTADA | REVERTIDA`. Desde `CREADA` o `SIMULADA` se puede pasar a `CANCELADA`. Cualquier otra transición lanza `EstadoInvalidoError`.
- **RN-26** La simulación lee la fuente, crea cada registro con su creador (Factory Method según el tipo: `CLIENTE`, `HOSTING`, `PAGO`), lo valida y escribe en el log una entrada `INFO` si es válido o `ERROR` con `describirErrores()` si no. No escribe datos de negocio.
- **RN-27** Confirmar = `aprobar()` y luego `prepararEjecucion(fuente)`, que vuelve a leer y comprueba que la cantidad de válidos sea igual a la de la simulación (si no, `ReglaNegocioError` "La fuente cambió desde la simulación"). Después escribe solo los válidos en una transacción, en el orden clientes → suscripciones → pagos. Si cualquier escritura falla, revierte todo y el proceso queda `REVERTIDA`. Si todo sale bien, queda `EJECUTADA`.
- **RN-28** Los clientes migrados no tienen cuenta de acceso. La vinculan en su primer ingreso (RN-07). Su tarjeta pasa por las validaciones de formato y vigencia, pero **no** por el validador externo.

## Contingencia

- **RN-29** El algoritmo activo se puede cambiar en ejecución entre **AES** (AES-256-GCM), **ChaCha20** (ChaCha20-Poly1305), **Camellia** (Camellia-256-CBC + HMAC-SHA256) y **Twofish** (Twofish-256-CTR + HMAC-SHA256). Cada registro guarda qué algoritmo lo cifró, así que se pueden descifrar registros cifrados con un algoritmo anterior.
- **RN-30** La sincronización reinserta los eventos en el orden en que se escribieron. Si alguno falla, se detiene, informa cuántos alcanzó a sincronizar y **no** vacía el medio.
