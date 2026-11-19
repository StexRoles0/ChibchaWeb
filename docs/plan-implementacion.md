# Plan de implementación

El trabajo se hace **por capas en el backend y por casos de uso en general**. Primero va la base común (fases 0 a 2) y luego se avanza CU por CU (fase 3), con backend y frontend en paralelo.

## Fase 0 — Andamiaje
- `docker-compose.yml` con `db` (postgres:16, que monta `schema.sql` y `seed_dev.sql`), `backend` (python:3.12), `frontend` (node:20 en desarrollo y nginx en producción, con proxy de `/api` al backend) y `tareas` (supercronic).
- `.env.example` con: `DJANGO_SECRET_KEY`, `DATABASE_URL`, `CLAVE_CIFRADO`, `ALGORITMO_CIFRADO=AES`, `RUTA_RESPALDO`, `SIMULAR_EXTERNOS=true`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_DISCOVERY_URL`.
- Backend: proyecto `config`, paquete `chibchaweb` con las carpetas de `backend/CLAUDE.md`, `pytest`, `ruff`, `import-linter`, `djangorestframework-camel-case`.
- Frontend: `ng new frontend --standalone --routing --style=scss`, `proxy.conf.json`, ESLint, tokens de diseño y el *shell* (barra superior + menú lateral).
- **Salida:** `docker compose up` levanta todo, y `lint-imports` y `pytest` corren (aunque no haya pruebas todavía).

## Fase 1 — Dominio completo + pruebas unitarias (backend-dev)
Todas las clases e interfaces de `modelo/dominio.md`, organizadas en módulos (`cuentas`, `hospedaje`, `facturacion`, `dominios_web`, `soporte`, `migracion`, `integraciones`, `respaldo`, `repositorios`, `errores`). Tienen que tener pruebas todas las reglas RN-01…RN-30 que viven en el dominio. Repositorios falsos en memoria en `tests/falsos.py`.

## Fase 2 — Persistencia + adaptadores (backend-dev)
`Mapeador<T>` (Layer Supertype) y los 7 mapeadores que implementan los repositorios. `UnidadDeTrabajoDjango`. Contingencia en los 4 mapeadores. Adaptadores reales y simulados. Pruebas de integración de cada mapeador contra PostgreSQL (ida y vuelta de cada agregado).

## Fase 3 — Por caso de uso (servicio → API → pantalla)
Se usa `/implementar-cu <CU>` en este orden, porque cada uno habilita al siguiente:

1. AUTH-01, AUTH-02, AUTH-03 (sin login no se puede probar nada más)
2. CLI-01, CLI-03, CLI-02
3. CON-01, CON-02 (la base de los listados)
4. EMP-01..04, DIS-01..04
5. SOP-01, SOP-02, SOP-03
6. DOM-01, DOM-02
7. FAC-01, COM-01, COM-02 (comandos)
8. MIG-01
9. RT04 (pantalla M-20 + pruebas de caída de BD)

## Fase 4 — Cierre
E2E con Playwright, uno por CU en su flujo principal más los flujos alternos clave (tarjeta `…0002` rechazada, escalar en el último nivel, migración revertida, BD caída con 503 y luego sincronización). Revisión final de conformidad con el modelo (`/revisar-conformidad`). Actualizar EA con `pendientes-modelo.md`.

## Tabla de avance

Estados: ⬜ pendiente · 🟨 en curso · ✅ terminado (cumple la definición de terminado de `CLAUDE.md`)

| CU | Servicio | API | Pantalla | Pruebas | Revisión |
|---|---|---|---|---|---|
| CU-AUTH-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-AUTH-02 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-AUTH-03 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-CLI-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-CLI-02 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-CLI-03 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-EMP-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-EMP-02 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-EMP-03 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-EMP-04 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-DIS-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-DIS-02 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-DIS-03 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-DIS-04 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-CON-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-CON-02 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-FAC-01 | ✅ | — (comando) | — | ✅ | ✅ |
| CU-DOM-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-DOM-02 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-COM-01 | ✅ | — (comando) | — | ✅ | ✅ |
| CU-COM-02 | ✅ | — (comando) | — | ✅ | ✅ |
| CU-SOP-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-SOP-02 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-SOP-03 | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU-MIG-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| RT04 | ✅ | ✅ | ✅ | ✅ | ✅ |
