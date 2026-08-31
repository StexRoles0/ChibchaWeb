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
| MOD-CLI | Gestión de Clientes |
| MOD-EMP | Gestión de Empleados y Distribuidores |
| MOD-CON | Consultas y Búsquedas |
| MOD-FAC | Facturación y Pagos |
| MOD-DOM | Gestión de Dominios |
| MOD-COM | Comisiones a Distribuidores |
| MOD-SOP | Soporte Técnico (Tickets) |
| MOD-MIG | Migración de Datos Legados |
| MOD-INF | Infraestructura y Calidad (transversal) |

## 3. Requerimientos funcionales

### MOD-CLI — Gestión de Clientes

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-CLI-01 | Crear perfil de cliente | Registrar información personal, del sitio web y del modo de pago del cliente | Alta |
| RF-CLI-02 | Modificar perfil de cliente | Permitir edición de los datos de un cliente existente | Alta |
| RF-CLI-03 | Eliminar perfil de cliente | Permitir borrado de un perfil de cliente | Media |
| RF-CLI-04 | Validar dirección y tarjeta | Validar dirección y tarjeta de crédito antes de persistir en base de datos | Alta |
| RF-CLI-05 | Selección de paquete y plan | Asociar al cliente un paquete (Platino/Plata/Oro) y un plan de pago (mensual/trimestral/semestral/anual) | Alta |

### MOD-EMP — Gestión de Empleados y Distribuidores

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-EMP-01 | Gestión de perfiles de empleados | CRUD de datos de empleados | Media |
| RF-EMP-02 | Gestión de perfiles de distribuidores | CRUD de datos de distribuidores, incluida categoría (Básico/Premium) | Alta |

### MOD-CON — Consultas y Búsquedas

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-CON-01 | Consulta básica | Vista resumida de clientes, empleados o distribuidores | Media |
| RF-CON-02 | Consulta detallada | Vista ampliada de un registro específico | Media |

### MOD-FAC — Facturación y Pagos

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-FAC-01 | Cargo a tarjeta de crédito | Cargar el monto del servicio de hosting a la tarjeta asociada | Alta |
| RF-FAC-02 | Soporte multi-franquicia | Aceptar VISA, MASTERCARD y DINERS | Alta |
| RF-FAC-03 | Facturación a distribuidores | Cobrar a clientes directos y a distribuidores autorizados (no a los clientes de los distribuidores) | Alta |

### MOD-DOM — Gestión de Dominios

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-DOM-01 | Registro de solicitud de dominio | Capturar la solicitud de registro/transferencia de dominio | Alta |
| RF-DOM-02 | Generación de XML | Generar archivo XML con formato definido para el registrador externo | Alta |
| RF-DOM-03 | Envío de solicitud | Enviar automáticamente la solicitud XML al registrador (deseable) | Baja |

### MOD-COM — Comisiones a Distribuidores

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-COM-01 | Cálculo de comisión | Calcular comisión (10% Básico / 15% Premium) según ventas del distribuidor | Alta |
| RF-COM-02 | Generación de cheques | Generar cheque a nombre del distribuidor por su comisión | Media |

### MOD-SOP — Soporte Técnico (Tickets)

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-SOP-01 | Registro de ticket | Registrar solicitud de soporte por novedad reportada en un sitio web | Alta |
| RF-SOP-02 | Consulta diaria de tickets | Permitir al equipo de soporte revisar tickets pendientes | Media |
| RF-SOP-03 | Enrutamiento por niveles de servicio | Enrutar el ticket entre niveles hasta su solución | Alta |

### MOD-MIG — Migración de Datos Legados

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RF-MIG-01 | Migración de registros legados | Migrar datos del sistema antiguo a la nueva plataforma | Media |
| RF-MIG-02 | Validación de datos migrados | Aplicar proceso de validación para garantizar confiabilidad de los datos migrados | Alta |

## 4. Requerimientos no funcionales

### MOD-INF — Infraestructura y Calidad

| Código | Título | Descripción | Prioridad |
|---|---|---|---|
| RNF-INF-01 | Desempeño | Diseño de la arquitectura que favorezca el atributo de calidad de desempeño (tiempos de respuesta, uso eficiente de recursos) | Alta |
| RNF-INF-02 | Mantenibilidad — Convenciones de nombrado | Aplicar convenciones de nombrado consistentes en todo el sistema para favorecer la mantenibilidad | Media |
| RNF-INF-03 | Modularidad y extensibilidad — Reuso de patrones de diseño | Aplicar patrones de diseño reconocidos que favorezcan la modularidad y extensibilidad del sistema | Alta |
| RNF-INF-04 | Contingencia de base de datos | Ante caída de BD, respaldar en archivo plano con cifrado configurable (1 de 4 algoritmos) | Alta |

## 5. Convenciones

- **Código**: prefijo `RF-` (funcional) o `RNF-` (no funcional) + módulo (3 letras) + número consecutivo de 2 dígitos.
- **Prioridad**: Alta / Media / Baja, según criticidad para el primer entregable (casos de uso base) y explicitud del enunciado (ej. lo marcado como "deseable" se prioriza como Baja).
- Este documento es la base para derivar los casos de uso en formato extendido del primer entregable (11 de septiembre de 2026).

---

*Última actualización: agosto de 2026.*
