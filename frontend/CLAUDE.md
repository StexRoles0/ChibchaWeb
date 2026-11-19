# Frontend — Angular 18+ (standalone, signals)

Lee primero `../CLAUDE.md`, `../docs/api.md` y `../docs/ui.md`. El frontend **solo** conoce el contrato REST. No sabe nada de dominio, servicios ni mapeadores del backend.

## Estructura

```
frontend/src/
├── app/
│   ├── core/
│   │   ├── api/
│   │   │   ├── dto.ts                # interfaces copiadas de docs/api.md (nombres del modelo)
│   │   │   ├── acceso.api.ts         # una clase *Api por servicio del backend:
│   │   │   ├── clientes.api.ts       #   AccesoApi, ClientesApi, EmpleadosApi, DistribuidoresApi,
│   │   │   ├── ...                   #   ConsultasApi, DominiosApi, SoporteApi, MigracionApi, ContingenciaApi
│   │   │   └── simulado/             # respuestas simuladas por endpoint (modo sin backend)
│   │   ├── auth/sesion.store.ts      # signal<ResultadoAccesoDTO | null>, carga GET /auth/sesion
│   │   ├── guardas.ts                # sinSesion, autenticado, esCliente, identidadPendiente, operacion('X')
│   │   ├── interceptores.ts          # errores (401→/acceso, 403, 503 banner), withCredentials
│   │   └── errores.ts                # ErrorApi {codigo, mensaje, campo?} + mapeo a mensajes
│   ├── layout/                       # shell: barra superior, menú lateral por rol, banner de contingencia
│   ├── features/
│   │   ├── acceso/                   # M-01, callback
│   │   ├── registro/                 # M-02..M-04 + registro.store.ts
│   │   ├── cliente/                  # M-05..M-09
│   │   ├── soporte/                  # M-10 (compartida), M-17
│   │   ├── gestion/                  # M-11..M-16 (formulario M-13 reutilizable empleado/distribuidor)
│   │   └── admin/                    # M-18..M-20
│   ├── shared/                       # tabla, etiqueta-estado, campo, dialogo-confirmacion, monto pipe
│   └── app.routes.ts                 # rutas y guardas de docs/ui.md
├── styles/                           # tokens.scss (docs/ui.md), base.scss, componentes.scss
└── environments/                     # apiBase: '/api/v1', simularApi: boolean
```

## Reglas

- Componentes **standalone**, `ChangeDetectionStrategy.OnPush`, estado con `signal`/`computed`, formularios con **Reactive Forms tipados** y control de flujo `@if`/`@for`.
- Cada feature carga sus rutas con `loadChildren`.
- Las llamadas HTTP van solo en `core/api/*.api.ts`. Los componentes no usan `HttpClient` directamente.
- Las interfaces de `dto.ts` se llaman igual que en el modelo (`ResumenDTO`, `DatosClienteDTO`, …). No inventes otras formas: si una pantalla necesita un dato que no está en el contrato, avisa al orquestador.
- Los errores 422 se muestran debajo del campo que indica `error.campo`. Los demás errores se muestran en un aviso arriba del formulario.
- Las validaciones del frontend (obligatorio, formato de correo, patrón de franquicia, 63 caracteres del dominio) son **solo ayuda** para el usuario. El backend siempre vuelve a validar.
- El monto se calcula con RN-01 solo como vista previa en M-03. Se usa aritmética en centavos, no `float` directo.
- Los textos de la interfaz van en español, con el tono de los mockups.
- Accesibilidad: cada `label` tiene `for`, el foco se ve, los diálogos atrapan el foco, el contraste es AA y las etiquetas de estado tienen texto además del color.

## Modo simulado (para trabajar en paralelo con el backend)

`environment.simularApi = true` activa `simuladoInterceptor`, que responde según `core/api/simulado/` con los datos de ejemplo de `docs/api.md` y `seed_dev.sql`. Esto deja trabajar en cada pantalla antes de que exista el endpoint. **Desde D-32 el desarrollo normal usa el backend real** (`environment.ts` tiene `simularApi: false`); el simulado es una opción explícita: `npm run start:simulado` (`ng serve --configuration simulado`, que reemplaza `environment.ts` por `environment.simulado.ts`). El modo simulado nunca se activa en el build de producción. Las respuestas del simulado deben tener **la misma forma** que las del backend real (literales de enum, `entradas` de migración, tipos técnicos de contingencia, etc.); si el backend cambia, se actualiza el simulado.

## Desarrollo

```bash
npm install
npm start                 # ng serve contra el backend REAL: proxy.conf.json, /api → http://localhost:8000
npm run start:simulado    # ng serve con el modo simulado (sin backend)
ng test --watch=false     # unidades (stores, guardas, interceptores, pipes, formularios)
ng lint
npm run e2e               # e2e completo desde cero en un entorno aislado (ver abajo)
```

Para el backend real: `docker compose up -d db backend` desde la raíz (API en `http://localhost:8000`, `SIMULAR_EXTERNOS=true`, BD sembrada con `docs/seed_dev.sql`). El proxy de `proxy.conf.json` **no** reescribe el encabezado `Host` (`changeOrigin: false`): así el `Origin` del navegador coincide con el `Host` que ve Django y la comprobación CSRF pasa en cualquier puerto de `ng serve` (con `changeOrigin: true` los POST fallaban con 403 `CSRF Failed: Origin checking failed` salvo en los puertos de `CSRF_TRUSTED_ORIGINS`). La etapa `dev` de Docker usa `proxy.conf.docker.json` (`http://backend:8000`) y también el backend real.

**E2E (Fase 4).** `npm run e2e` recrea el proyecto Docker aislado `chibchaweb_e2e` (`../docker-compose.e2e.yml`: BD propia sembrada con `schema.sql` + `seed_dev.sql`, backend con `SIMULAR_EXTERNOS=true` en :18000 y `ng serve` real en :14200; no toca `datos_pg16` ni los puertos 5433/8000/4200/8080), corre `playwright test` (`e2e/<cu>.spec.ts`, un worker, sin reintentos) y al terminar lo apaga con `down -v` (solo de ese proyecto). `E2E_MANTENER=1 npm run e2e` lo deja arriba; con el entorno arriba, `npm run e2e:playwright -- rt04` corre solo una parte (la BD acumula datos: la prueba de MIG-01 se salta si ya hubo migración real). Los CU sin pantalla (FAC-01, COM-01/02) ejecutan `manage.py` dentro del contenedor y verifican por la interfaz y con SQL de solo lectura; RT04 detiene y arranca el contenedor `db`. Informe en `playwright-report/` (ignorado por git).

Login en desarrollo: con el proveedor simulado, M-01 muestra el campo "correo de prueba" (solo si `!environment.production`), que manda el código `dev:<correo>`. Correos sembrados: `gestion@`, `soporte@` y `admin@chibchaweb.co`. Cualquier otro correo pasa por el registro.
