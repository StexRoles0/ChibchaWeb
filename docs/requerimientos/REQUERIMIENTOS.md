# Documentación de Requerimientos — ChibchaWeb

**Asignatura:** Fundamentos de Ingeniería de Software
**Proyecto Semestral:** 2026-III
**Universidad Distrital Francisco José de Caldas**

## Tabla de contenido

- [1. Contexto](#1-contexto)
- [2. Actores](#2-actores)
- [3. Módulos del sistema](#3-módulos-del-sistema)
- [4. Requerimientos funcionales](#4-requerimientos-funcionales)
- [5. Requerimientos no funcionales](#5-requerimientos-no-funcionales)
- [6. Trazabilidad con el enunciado original](#6-trazabilidad-con-el-enunciado-original)
- [7. Convenciones](#7-convenciones)

---

## 1. Contexto

ChibchaWeb es una empresa de hospedaje web ubicada en Sugamuxi, con clientes en Colombia y países vecinos, y expansión próxima a África. Ofrece tres paquetes de hosting (Platino, Plata, Oro) sobre plataformas Windows y Unix, cuatro planes de pago (mensual, trimestral, semestral, anual) y trabaja con distribuidores externos categorizados como **Básico** (≤100 dominios, comisión 10%) y **Premium** (>100 dominios, comisión 15%).

## 2. Actores

El sistema define un actor genérico `Usuario`, del cual se especializan (generalización UML) los actores concretos que interactúan con el sistema. Adicionalmente existe un actor no humano que representa procesos automáticos disparados por tiempo/evento.

```
Usuario
├── Cliente
├── Distribuidor
└── Empleado
    ├── Administrador
    └── Empleado de Soporte

Programador de Tareas / Sistema   (actor no humano, procesos automáticos)
```

- **Cliente**: se autoregistra, gestiona su propio perfil, solicita dominios y reporta tickets.
- **Distribuidor**: su perfil es creado por el Administrador; no se autoregistra ni se autogestiona.
- **Empleado**: actor base administrativo; por sí solo no ejecuta casos de uso directamente, se especializa en:
  - **Administrador**: gestiona empleados, distribuidores, consultas administrativas y migración de datos.
  - **Empleado de Soporte**: gestiona los tickets de soporte técnico.
- **Programador de Tareas / Sistema**: dispara procesos automáticos que no requieren intervención humana directa (cobros periódicos, cálculo de comisiones).

## 3. Módulos del sistema

| Código | Módulo |
|---|---|
| MOD-AUTH | Autenticación (transversal) |
| MOD-CLI | Gestión de Clientes |
| MOD-EMP | Gestión de Empleados y Distribuidores |
| MOD-CON | Consultas y Búsquedas |
| MOD-FAC | Facturación y Pagos |
| MOD-DOM | Gestión de Dominios |
| MOD-COM | Comisiones a Distribuidores |
| MOD-SOP | Soporte Técnico (Tickets) |
| MOD-MIG | Migración de Datos Legados |
| MOD-INF | Infraestructura y Calidad (transversal) |

## 4. Requerimientos funcionales

Cada sub-requerimiento indica el **actor** responsable y, cuando aplica, su relación con otros casos de uso (fachada por generalización, `«include»` obligatorio, `«extend»` opcional). Los nombres coinciden exactamente con los elementos `Use Case` creados en Enterprise Architect.

### MOD-AUTH — Autenticación

| Código | Caso de uso (EA) | Actor | Descripción | Prioridad |
|---|---|---|---|---|
| RF-AUTH-01 | CU-AUTH-01_IniciarSesion | Usuario | Autenticación de cualquier actor registrado en el sistema | Alta |
| RF-AUTH-02 | CU-AUTH-02_Registrarse | Cliente | Autoregistro del cliente: cuenta + información personal, del sitio web y modo de pago. Incluye (`«include»`) la validación de dirección/tarjeta y la selección de paquete y plan | Alta |

### MOD-CLI — Gestión de Clientes

| Código | Caso de uso (EA) | Actor | Descripción | Prioridad |
|---|---|---|---|---|
| RF-CLI-01 | CU-CLI-01_GestionarPerfil *(fachada)* | Cliente | Punto de acceso a la autogestión del perfil; generaliza a Modificar y Eliminar | Alta |
| RF-CLI-02 | CU-CLI-02_ModificarPerfil | Cliente | Edición de los datos del propio perfil. Extiende (`«extend»`, opcional) la validación de dirección/tarjeta y la selección de paquete y plan, solo si el cliente decide cambiarlos | Alta |
| RF-CLI-03 | CU-CLI-03_EliminarPerfil | Cliente | Borrado del propio perfil de cliente | Media |
| RF-CLI-04 | CU-CLI-04_ValidarDireccionTarjeta | *(sin actor directo)* | Validación de dirección y tarjeta antes de persistir en base de datos. Reutilizado desde `Registrarse` (`include`) y `ModificarPerfil` (`extend`) | Alta |
| RF-CLI-05 | CU-CLI-05_SeleccionarPaqueteYPlan | *(sin actor directo)* | Asociación de paquete (Platino/Plata/Oro) y plan de pago (mensual/trimestral/semestral/anual). Reutilizado desde `Registrarse` (`include`) y `ModificarPerfil` (`extend`) | Alta |

> Nota: la creación de perfil de cliente **no** es un caso de uso independiente en este módulo — corresponde a `CU-AUTH-02_Registrarse` (ver MOD-AUTH).

### MOD-EMP — Gestión de Empleados y Distribuidores

Actor exclusivo: **Administrador**. El Distribuidor no se autogestiona; su perfil es creado y administrado por el Administrador.

| Código | Caso de uso (EA) | Actor | Descripción | Prioridad |
|---|---|---|---|---|
| RF-EMP-01 | CU-EMP-01_GestionarEmpleado *(fachada)* | Administrador | Punto de acceso a la gestión de empleados; generaliza a Crear, Modificar y Eliminar | Media |
| RF-EMP-02 | CU-EMP-02_CrearEmpleado | Administrador | Alta de un nuevo perfil de empleado | Media |
| RF-EMP-03 | CU-EMP-03_ModificarEmpleado | Administrador | Edición de un perfil de empleado existente (precondición: empleado ya creado) | Media |
| RF-EMP-04 | CU-EMP-04_EliminarEmpleado | Administrador | Borrado de un perfil de empleado (precondición: empleado ya creado) | Media |
| RF-EMP-05 | CU-EMP-05_GestionarDistribuidor *(fachada)* | Administrador | Punto de acceso a la gestión de distribuidores; generaliza a Crear, Modificar y Eliminar | Alta |
| RF-EMP-06 | CU-EMP-06_CrearDistribuidor | Administrador | Alta de un nuevo perfil de distribuidor, incluida su categoría (Básico/Premium) | Alta |
| RF-EMP-07 | CU-EMP-07_ModificarDistribuidor | Administrador | Edición de un perfil de distribuidor existente (precondición: distribuidor ya creado) | Alta |
| RF-EMP-08 | CU-EMP-08_EliminarDistribuidor | Administrador | Borrado de un perfil de distribuidor (precondición: distribuidor ya creado) | Media |

### MOD-CON — Consultas y Búsquedas

Actor exclusivo: **Administrador**. La entidad consultada (Cliente, Empleado o Distribuidor) se documenta como parámetro dentro de la especificación extendida de cada caso de uso, no como casos de uso separados.

| Código | Caso de uso (EA) | Actor | Descripción | Prioridad |
|---|---|---|---|---|
| RF-CON-01 | CU-CON-01_Consultar *(fachada)* | Administrador | Punto de acceso a las consultas; generaliza a Básica y Detallada | Media |
| RF-CON-02 | CU-CON-02_ConsultaBasica | Administrador | Vista resumida de la entidad seleccionada (Cliente, Empleado o Distribuidor) | Media |
| RF-CON-03 | CU-CON-03_ConsultaDetallada | Administrador | Vista ampliada de un registro específico de la entidad seleccionada | Media |

### MOD-FAC — Facturación y Pagos

| Código | Caso de uso (EA) | Actor | Descripción | Prioridad |
|---|---|---|---|---|
| RF-FAC-01 | CU-FAC-01_CargarPago | Programador de Tareas / Sistema | Cargo automático del monto de hosting a la tarjeta (VISA/MASTERCARD/DINERS) asociada. Sujeto de cobro (Cliente o Distribuidor) documentado como parámetro; ChibchaWeb cobra directamente a clientes y a distribuidores autorizados, no a los clientes de estos últimos | Alta |

### MOD-DOM — Gestión de Dominios

| Código | Caso de uso (EA) | Actor | Descripción | Prioridad |
|---|---|---|---|---|
| RF-DOM-01 | CU-DOM-01_RegistrarSolicitudDominio | Cliente | Captura de la solicitud de registro/transferencia de dominio. Incluye (`«include»`) la generación de XML y el envío de la solicitud | Alta |
| RF-DOM-02 | CU-DOM-02_GenerarXML | *(sin actor directo)* | Generación del archivo XML con formato definido para el registrador externo | Alta |
| RF-DOM-03 | CU-DOM-03_EnviarSolicitud | *(sin actor directo)* | Envío de la solicitud XML al registrador de dominio externo | Baja |

### MOD-COM — Comisiones a Distribuidores

| Código | Caso de uso (EA) | Actor | Descripción | Prioridad |
|---|---|---|---|---|
| RF-COM-01 | CU-COM-01_CalcularComision | Programador de Tareas / Sistema | Cálculo automático de comisión (10% Básico / 15% Premium) según categoría del distribuidor. Incluye (`«include»`) la generación del cheque | Alta |
| RF-COM-02 | CU-COM-02_GenerarCheque | *(sin actor directo)* | Generación del cheque a nombre del distribuidor por su comisión | Media |

### MOD-SOP — Soporte Técnico (Tickets)

Tres casos de uso independientes, sin fachada (actores distintos, no son variantes de un mismo concepto).

| Código | Caso de uso (EA) | Actor | Descripción | Prioridad |
|---|---|---|---|---|
| RF-SOP-01 | CU-SOP-01_RegistrarTicket | Cliente | Registro de una novedad/problema reportado sobre un sitio web | Alta |
| RF-SOP-02 | CU-SOP-02_ConsultarTicketsDiario | Empleado de Soporte | Revisión diaria de los tickets generados | Media |
| RF-SOP-03 | CU-SOP-03_EnrutarPorNivelServicio | Empleado de Soporte | Enrutamiento manual del ticket entre niveles de servicio hasta su solución (precondición: ticket registrado y revisado) | Alta |

### MOD-MIG — Migración de Datos Legados

| Código | Caso de uso (EA) | Actor | Descripción | Prioridad |
|---|---|---|---|---|
| RF-MIG-01 | CU-MIG-01_MigrarRegistrosLegados | Administrador | Migración de registros del sistema legado a la nueva plataforma. Incluye (`«include»`) la validación de los datos migrados | Media |
| RF-MIG-02 | CU-MIG-02_ValidarDatosMigrados | *(sin actor directo)* | Validación obligatoria de confiabilidad de los datos migrados | Alta |

## 5. Requerimientos no funcionales

### MOD-INF — Infraestructura y Calidad

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RNF-INF-01 | Desempeño | Diseño de la arquitectura que favorezca el atributo de calidad de desempeño (tiempos de respuesta, uso eficiente de recursos) | Alta |
| RNF-INF-02 | Mantenibilidad — Convenciones de nombrado | Aplicar convenciones de nombrado consistentes en todo el sistema para favorecer la mantenibilidad | Media |
| RNF-INF-03 | Modularidad y extensibilidad — Reuso de patrones de diseño | Aplicar patrones de diseño reconocidos que favorezcan la modularidad y extensibilidad del sistema | Alta |
| RNF-INF-04 | Contingencia de base de datos | Ante caída de BD, respaldar en archivo plano con cifrado configurable (1 de 4 algoritmos) | Alta |

## 6. Trazabilidad con el enunciado original

Los códigos `RF-MODULO-NN` de este documento son una descomposición de trabajo; no reemplazan a los requerimientos originales del enunciado, que se modelan en Enterprise Architect como elementos `<<Requirement>>` (`RF01`–`RF08`, `RT01`–`RT04`) dentro de `01_Requirements`, con su texto tal cual aparece en `ProySemestre202603.md`. La Relationship Matrix (`04_Traceability`, filtro `Realize`) es la fuente de verdad sobre qué caso de uso cubre cada requerimiento original.

| Requerimiento original | Casos de uso que lo realizan (`«Realize»`) |
|---|---|
| RF01 | CU-CLI-01_GestionarPerfil (fachada; incluye a Modificar/Eliminar por generalización); creación cubierta por CU-AUTH-02_Registrarse |
| RF02 | CU-EMP-01_GestionarEmpleado, CU-EMP-05_GestionarDistribuidor (fachadas) |
| RF03 | CU-CON-01_Consultar (fachada) |
| RF04 | CU-FAC-01_CargarPago |
| RF05 | CU-DOM-01_RegistrarSolicitudDominio |
| RF06 | CU-COM-01_CalcularComision |
| RF07 | CU-SOP-01_RegistrarTicket, CU-SOP-02_ConsultarTicketsDiario, CU-SOP-03_EnrutarPorNivelServicio (sin fachada, actores distintos) |
| RF08 | CU-MIG-01_MigrarRegistrosLegados |
| RT01–RT03 | Sin caso de uso asociado (requerimientos de arquitectura/calidad, se abordan en el modelado estructural de octubre) |
| RT04 | Sin caso de uso asociado en este entregable; contingencia de base de datos, pertenece al modelado estructural de octubre |

> El caso de uso `CU-AUTH-01_IniciarSesion` no realiza directamente ningún RF numerado — es un requisito implícito de acceso, documentado como precondición en la especificación extendida de los demás casos de uso.

## 7. Convenciones

- **Código de sub-requerimiento**: prefijo `RF-` (funcional) o `RNF-` (no funcional) + módulo (3-4 letras) + número consecutivo de 2 dígitos. Distinto de los códigos `RF01`–`RF08`/`RT01`–`RT04` del enunciado original, que se conservan sin modificar como elementos `<<Requirement>>` en Enterprise Architect (ver sección 6).
- **Prioridad**: Alta / Media / Baja, según criticidad para el primer entregable (casos de uso base) y explicitud del enunciado (ej. lo marcado como "deseable" se prioriza como Baja).
- **Fachada (generalización entre casos de uso)**: se usa cuando 2 o más casos de uso comparten el mismo actor y representan una sola entrada conceptual de menú/interfaz que se bifurca en acciones concretas (ej. `GestionarPerfil` → Modificar/Eliminar). No se aplica por defecto en todos los módulos — solo cuando el criterio anterior se cumple.
- **`«include»`**: relación obligatoria; el caso de uso base siempre ejecuta al incluido (ej. `Registrarse` → `ValidarDireccionTarjeta`).
- **`«extend»`**: relación opcional/condicional; el caso de uso base puede o no disparar al extendido (ej. `ModificarPerfil` → `ValidarDireccionTarjeta`, solo si el cliente decide cambiar esos datos).
- Precondiciones de dependencia entre casos de uso (ej. "no se puede modificar sin haber creado antes") se documentan como texto en la especificación extendida, no como relación gráfica en el diagrama.
- Este documento es la base para derivar los casos de uso en formato extendido del primer entregable (11 de septiembre de 2026).

---

*Última actualización: agosto de 2026.*
