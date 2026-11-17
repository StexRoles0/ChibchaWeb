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

`environment.simularApi = true` activa `simuladoInterceptor`, que responde según `core/api/simulado/` con los datos de ejemplo de `docs/api.md` y `seed_dev.sql`. Esto deja trabajar en cada pantalla antes de que exista el endpoint. Cuando el endpoint está listo, se apaga para esa ruta y se prueba contra el backend real. El modo simulado nunca se activa en el build de producción.

## Desarrollo

```bash
npm install
npm start                 # ng serve con proxy.conf.json: /api → http://localhost:8000
ng test --watch=false     # unidades (stores, guardas, interceptores, pipes, formularios)
ng lint
npx playwright test       # e2e (requiere backend con SIMULAR_EXTERNOS=true)
```

Login en desarrollo: con el proveedor simulado, M-01 muestra el campo "correo de prueba" (solo si `!environment.production`), que manda el código `dev:<correo>`. Correos sembrados: `gestion@`, `soporte@` y `admin@chibchaweb.co`. Cualquier otro correo pasa por el registro.
