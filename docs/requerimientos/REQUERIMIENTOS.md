# Documentación de Requerimientos — ChibchaWeb

**Asignatura:** Fundamentos de Ingeniería de Software
**Proyecto Semestral:** 2026-III
**Universidad Distrital Francisco José de Caldas**

## Tabla de contenido

- [1. Contexto](#1-contexto)
- [2. Módulos del sistema](#2-módulos-del-sistema)
- [3. Requerimientos funcionales](#3-requerimientos-funcionales)
- [4. Requerimientos no funcionales](#4-requerimientos-no-funcionales)
- [5. Convenciones](#5-convenciones)

---

## 1. Contexto

ChibchaWeb es una empresa de hospedaje web ubicada en Sugamuxi, con clientes en Colombia y países vecinos, y expansión próxima a África. Ofrece tres paquetes de hosting (Platino, Plata, Oro) sobre plataformas Windows y Unix, cuatro planes de pago (mensual, trimestral, semestral, anual) y trabaja con distribuidores externos categorizados como **Básico** (≤100 dominios, comisión 10%) y **Premium** (>100 dominios, comisión 15%).

## 2. Módulos del sistema

| Código | Módulo |
|---|---|
| MOD-AUTH | Autenticación (transversal) |
| MOD-CLI | Gestión de Clientes |
| MOD-EMP | Gestión de Empleados |
| MOD-DIS | Gestión de Distribuidores |
| MOD-CON | Consultas y Búsquedas |
| MOD-FAC | Facturación y Pagos |
| MOD-DOM | Gestión de Dominios |
| MOD-COM | Comisiones a Distribuidores |
| MOD-SOP | Soporte Técnico (Tickets) |
| MOD-MIG | Migración de Datos Legados |
| MOD-INF | Infraestructura y Calidad (transversal) |

## 3. Requerimientos funcionales

### MOD-AUTH — Autenticación

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-AUTH-01 | Iniciar sesión | Autenticación de cualquier actor registrado en el sistema | Alta |
| RF-AUTH-02 | Registrarse | Autoregistro del cliente: cuenta, información personal, del sitio web (con dominio asignado por defecto), modo de pago, paquete/plan y validación de dirección/tarjeta. Incluye opcionalmente un código de distribuidor referente | Alta |

### MOD-CLI — Gestión de Clientes

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-CLI-01 | Gestionar perfil | Punto de acceso del cliente a la administración de su propio perfil | Alta |
| RF-CLI-02 | Modificar perfil | Edición de los datos del propio perfil; permite opcionalmente actualizar dirección/tarjeta y cambiar de paquete/plan | Alta |
| RF-CLI-03 | Eliminar perfil | Borrado del propio perfil de cliente | Media |
| RF-CLI-04 | Validar dirección y tarjeta | Validación de dirección y tarjeta de crédito antes de persistir en base de datos | Alta |
| RF-CLI-05 | Seleccionar paquete y plan | Asociación de paquete (Platino/Plata/Oro) y plan de pago (mensual/trimestral/semestral/anual) | Alta |

### MOD-EMP — Gestión de Empleados

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-EMP-01 | Gestionar empleado | Punto de acceso a la administración de empleados | Media |
| RF-EMP-02 | Crear empleado | Alta de un nuevo perfil de empleado | Media |
| RF-EMP-03 | Modificar empleado | Edición de un perfil de empleado existente | Media |
| RF-EMP-04 | Eliminar empleado | Borrado de un perfil de empleado | Media |

### MOD-DIS — Gestión de Distribuidores

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-DIS-01 | Gestionar distribuidor | Punto de acceso a la administración de distribuidores | Alta |
| RF-DIS-02 | Crear distribuidor | Alta de un nuevo perfil de distribuidor, incluida su categoría (Básico/Premium) | Alta |
| RF-DIS-03 | Modificar distribuidor | Edición de un perfil de distribuidor existente | Alta |
| RF-DIS-04 | Eliminar distribuidor | Borrado de un perfil de distribuidor | Media |

### MOD-CON — Consultas y Búsquedas

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-CON-01 | Consulta básica | Vista resumida de la entidad seleccionada (Cliente, Empleado o Distribuidor) según el rol de quien consulta | Media |
| RF-CON-02 | Consulta detallada | Vista ampliada de un registro específico, a la que se accede desde la consulta básica | Media |

### MOD-FAC — Facturación y Pagos

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-FAC-01 | Cargar pago | Cargo automático del monto de hosting a la tarjeta (VISA/MASTERCARD/DINERS) asociada, al vencimiento del plan. Aplica tanto a clientes directos como a distribuidores autorizados; no incluye lo que el distribuidor cobra a sus propios clientes, fuera del alcance del sistema | Alta |

### MOD-DOM — Gestión de Dominios

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-DOM-01 | Gestionar dominio | Punto de acceso del cliente a la solicitud de dominios | Alta |
| RF-DOM-02 | Registrar dominio nuevo | Solicitud de registro de un dominio nuevo | Alta |
| RF-DOM-03 | Transferir dominio | Solicitud de transferencia de un dominio existente | Baja |
| RF-DOM-04 | Generar XML | Generación del archivo XML con formato definido para el registrador externo | Alta |
| RF-DOM-05 | Enviar solicitud | Envío de la solicitud XML al registrador de dominio externo | Baja |

### MOD-COM — Comisiones a Distribuidores

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-COM-01 | Calcular comisión | Cálculo automático de comisión (10% Básico / 15% Premium) sobre los pagos de clientes registrados con el código del distribuidor | Alta |
| RF-COM-02 | Generar cheque | Generación del cheque a nombre del distribuidor por su comisión | Media |

### MOD-SOP — Soporte Técnico (Tickets)

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-SOP-01 | Registrar ticket | Registro de una novedad/problema reportado sobre un sitio web | Alta |
| RF-SOP-02 | Consultar tickets diario | Revisión diaria de los tickets generados | Media |
| RF-SOP-03 | Enrutar por nivel de servicio | Escalamiento del ticket a otro nivel de servicio cuando no se resuelve en el nivel actual | Alta |

### MOD-MIG — Migración de Datos Legados

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-MIG-01 | Migrar registros legados | Migración de registros del sistema legado a la nueva plataforma | Media |
| RF-MIG-02 | Validar datos migrados | Validación obligatoria de confiabilidad de los datos migrados | Alta |

## 4. Requerimientos no funcionales

### MOD-INF — Infraestructura y Calidad

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RNF-INF-01 | Desempeño | Diseño de la arquitectura que favorezca el atributo de calidad de desempeño (tiempos de respuesta, uso eficiente de recursos) | Alta |
| RNF-INF-02 | Mantenibilidad — Convenciones de nombrado | Aplicar convenciones de nombrado consistentes en todo el sistema para favorecer la mantenibilidad | Media |
| RNF-INF-03 | Modularidad y extensibilidad — Reuso de patrones de diseño | Aplicar patrones de diseño reconocidos que favorezcan la modularidad y extensibilidad del sistema | Alta |
| RNF-INF-04 | Contingencia de base de datos | Ante caída de BD, respaldar en archivo plano con cifrado configurable (1 de 4 algoritmos) | Alta |

## 5. Convenciones

- **Código**: prefijo `RF-` (funcional) o `RNF-` (no funcional) + módulo (3-4 letras) + número consecutivo de 2 dígitos.
- **Prioridad**: Alta / Media / Baja, según criticidad para el primer entregable (casos de uso base) y explicitud del enunciado (ej. lo marcado como "deseable" se prioriza como Baja).
- Este documento es la base para derivar los casos de uso en formato extendido del primer entregable (11 de septiembre de 2026); el detalle de actores, relaciones (`include`/`extend`) y trazabilidad hacia los requerimientos originales del enunciado se documenta directamente en Enterprise Architect (`01_Requirements`, `02_Use Case Model`, `04_Traceability`).

---

*Última actualización: septiembre de 2026.*
