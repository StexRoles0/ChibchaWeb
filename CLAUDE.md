# ChibchaWEB — contexto del proyecto

ChibchaWEB es una empresa ficticia de hosting web. Este repositorio tiene el **prototipo funcional** del proyecto semestral de Fundamentos de Ingeniería de Software (Universidad Distrital, 2026-III). Lo hace Steven Navarro Parrales y lo revisa el docente Henry Alberto Diosa.

El alcance está **cerrado y firmado**: son 25 casos de uso y 4 requerimientos técnicos (ver `docs/casos-de-uso.md`). No se agregan ni se quitan casos de uso. La nota final se pone comparando el código con el modelado estructural, así que **el código tiene que coincidir con el modelo**: mismos nombres de clases, atributos, métodos y relaciones.

Idioma de trabajo: **español**. Esto aplica al código del dominio, a los mensajes, a los commits y a la documentación.

## Estructura del monorepo

```
backend/     Django 5 + DRF + PostgreSQL 16 → ver backend/CLAUDE.md
frontend/    Angular 18+ (standalone) → ver frontend/CLAUDE.md
docs/        modelo y contratos (fuente de verdad) → ver índice abajo
docker-compose.yml   db (postgres), backend, frontend
```

## Arquitectura: la regla que no se rompe

```
frontend (Angular) ──HTTP/JSON──▶ web (vistas DRF) ──DTO──▶ servicio ──▶ dominio ◀── persistencia (mapeadores)
                                                                         ▲
                                                             adaptadores ┘ (implementan interfaces del dominio)
```

1. **El servicio solo habla con el dominio.** Usa las clases del dominio, las interfaces de integración (`ProveedorAutenticacion`, `PasarelaPago`, …) y las **interfaces de repositorio** (`RepositorioUsuario`, …). **Nunca importa un mapeador, un modelo ORM, `django.db` ni DRF.**
2. **El dominio es puro.** No importa Django, DRF, ni las capas `servicio`, `persistencia`, `adaptadores` o `web`. Define las interfaces que otras capas implementan. La única excepción es `dominio.respaldo`, que puede usar `cryptography`.
3. **La persistencia implementa los repositorios.** Cada `MapeadorX` hereda de `Mapeador<T>` e implementa `RepositorioX`. Traduce entre objetos del dominio y tablas.
4. **Los adaptadores implementan las interfaces de integración.** Son la única capa que conoce las API externas.
5. **La capa web solo conoce servicios y DTO.** No toca el dominio, los mapeadores ni los adaptadores.
6. **Solo el contenedor (`backend/config/contenedor.py`) conoce todas las capas.** Ahí se construyen los mapeadores y los adaptadores y se inyectan a los servicios.

`lint-imports` (import-linter, con la configuración en `backend/.importlinter`) hace cumplir estas reglas. Un PR que lo rompa no se acepta. El detalle está en `docs/arquitectura.md`.

> Corrección respecto al diagrama DC-SRV-01: allí los servicios tienen atributos de tipo `MapeadorX`. Ese diagrama está equivocado. En el código los servicios tienen atributos de tipo `RepositorioX`. Ver `docs/pendientes-modelo.md`.

## Reglas de nombrado

- **Python:** las clases conservan el nombre exacto del modelo (`ServicioSoporte`, `TarjetaCredito`). Los métodos y atributos pasan a `snake_case` de forma mecánica: `enrutarPorNivelServicio` → `enrutar_por_nivel_servicio`, `fechaCorte` → `fecha_corte`. Los atributos privados del modelo (`-`) llevan `_` delante y se exponen con `@property`. Las enumeraciones son `enum.Enum` con los literales exactos.
- **TypeScript/Angular:** las interfaces DTO conservan el nombre del modelo. Los campos JSON van en `camelCase`, igual que en el modelo (`idUsuario`, `tipoUsuario`). DRF convierte con `djangorestframework-camel-case`.
- **BD:** las tablas y columnas son las de `docs/schema.sql`, que no se cambia sin actualizar el documento ER.
- No inventes clases públicas nuevas en dominio o servicio. Si de verdad hace falta una, agrégala a `docs/pendientes-modelo.md` y avisa.

## Documentación (leer antes de implementar)

| Archivo | Para qué |
|---|---|
| `docs/arquitectura.md` | capas, dependencias, flujo de una petición, contenedor, transacciones |
| `docs/modelo/dominio.md` | las clases del dominio, con atributos, métodos y repositorios |
| `docs/modelo/servicio.md` | servicios y DTO |
| `docs/modelo/persistencia.md` | mapeadores |
| `docs/modelo/adaptadores.md` | adaptadores externos |
| `docs/reglas-negocio.md` | tarifas, descuentos, validaciones, estados, comisiones |
| `docs/casos-de-uso.md` | los 25 CU con actor, flujo, método de servicio, endpoint y pantalla |
| `docs/api.md` | contrato REST que comparten backend y frontend |
| `docs/ui.md` + `docs/ui/mockups/` | pantallas M-01…M-20, rutas, navegación por rol, tokens de diseño |
| `docs/base-de-datos.md` + `docs/schema.sql` + `docs/seed_dev.sql` | modelo relacional y datos de desarrollo |
| `docs/decisiones.md` | decisiones técnicas tomadas y su motivo |
| `docs/pendientes-modelo.md` | diferencias entre el código y el modelo en EA (hay que actualizar EA) |
| `docs/plan-implementacion.md` | fases, orden de trabajo y tabla de avance por CU |

## Modo orquestador

La sesión principal coordina el trabajo y lo delega en subagentes (`.claude/agents/`). No escribe el código grande ella misma.

- `backend-dev`: dominio, persistencia, servicios, API y pruebas del backend.
- `frontend-dev`: Angular, consume `docs/api.md`.
- `qa-pruebas`: pruebas de integración y e2e por caso de uso.
- `revisor-arquitectura`: solo lectura. Revisa capas, nombres contra el modelo y cobertura del CU. **Siempre interviene antes de dar un CU por terminado.**

Cómo trabajar:

1. Usa `/implementar-cu CU-XXX-NN` para cada caso de uso.
2. Backend y frontend pueden avanzar en paralelo porque el contrato está fijado en `docs/api.md`. El frontend usa datos simulados mientras el endpoint no exista.
3. Si un subagente encuentra una contradicción entre documentos, para y la reporta. No elige por su cuenta. La prioridad es: modelo (`docs/modelo/`) > `reglas-negocio.md` > `api.md` > `ui.md`.
4. Actualiza la tabla de avance de `docs/plan-implementacion.md` al cerrar cada CU.

## Definición de terminado (por CU)

- [ ] El método de servicio existe con la firma del modelo y su lógica de negocio vive en el dominio, no en el servicio ni en la vista.
- [ ] Hay pruebas unitarias del dominio (sin BD), pruebas del servicio con repositorios falsos en memoria y una prueba de integración del endpoint con PostgreSQL.
- [ ] El endpoint cumple `docs/api.md` (ruta, verbo, cuerpo, códigos de error).
- [ ] La pantalla se parece al mockup, respeta la navegación del rol y maneja los errores.
- [ ] `lint-imports`, `ruff`, `pytest`, `ng lint` y `ng test` pasan.
- [ ] `revisor-arquitectura` aprobó el CU.

## Comandos

```bash
docker compose up -d db                                    # postgres con schema.sql + seed_dev.sql
cd backend && pytest && lint-imports && ruff check .       # backend
cd backend && python manage.py runserver                   # API en :8000
cd backend && python manage.py cargar_pagos --fecha 2026-12-01   # CU-FAC-01 (tarea programada)
cd frontend && npm start                                    # :4200 con proxy a /api
cd frontend && ng test --watch=false && ng lint
```

## Prohibido

- Que el servicio importe algo de `persistencia`, `adaptadores` o `web`, o algo de Django ORM o DRF.
- Meter lógica de negocio en vistas, serializers o mapeadores. Validaciones, cálculos y transiciones de estado van en el dominio.
- Guardar `codigoSeguridad` o el número de tarjeta sin cifrar. Registrar en logs datos de la tarjeta.
- Borrar físicamente usuarios. Las bajas son lógicas (`activo = false`).
- Cambiar `docs/schema.sql` o `docs/api.md` sin decirlo y sin dejarlo anotado en `docs/decisiones.md`.
- Leer o escribir `.env` con secretos reales.
