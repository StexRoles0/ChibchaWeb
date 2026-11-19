---
name: implementar-cu
description: Orquesta la implementación completa de un caso de uso de ChibchaWEB (servicio, dominio, repositorio, endpoint, pantalla, pruebas y revisión) delegando en los subagentes.
when_to_use: Cuando el usuario pida implementar, continuar o terminar un caso de uso (CU-AUTH-01, CU-SOP-03, RT04, etc.).
argument-hint: "<código CU, p. ej. CU-SOP-03>"
disable-model-invocation: true
---

# Implementar $ARGUMENTS

Eres el orquestador. Coordina el trabajo y deja la programación a los subagentes.

## 1. Trazar el CU (lo haces tú)

Lee `docs/casos-de-uso.md` (fila y flujo de **$ARGUMENTS**), `docs/plan-implementacion.md` y `docs/pendientes-modelo.md`. Arma esta traza y muéstrala:

| Elemento | Valor |
|---|---|
| Actor y permiso | … |
| Método(s) de servicio (firma del modelo) | `ServicioX.metodo(params): Retorno` |
| Clases/métodos del dominio involucrados | … (de `docs/modelo/dominio.md`) |
| Repositorios y métodos | `RepositorioX.metodo` |
| Adaptadores | … |
| Reglas | RN-.. |
| Endpoint(s) | verbo + ruta + DTO (de `docs/api.md`) |
| Pantalla(s) y ruta Angular | M-.. (de `docs/ui.md`) |
| Flujos alternos → código HTTP | … |

Revisa también qué depende de otros CU que todavía no están (por ejemplo, si falta login). Si falta algo de las fases 1 y 2 (dominio o mapeadores), encárgalo primero.

## 2. Delegar en paralelo

- **backend-dev:** "Implementa $ARGUMENTS según esta traza: <traza>. Incluye las pruebas del dominio, del servicio con repositorios en memoria, de persistencia si hace falta y del endpoint."
- **frontend-dev** (al mismo tiempo, en modo simulado si el endpoint no existe): "Implementa las pantallas de $ARGUMENTS según esta traza: <traza>. Mira primero el mockup."

Pásale a cada uno la traza completa, porque no comparten tu contexto.

## 3. Integrar y probar

Cuando los dos terminen, pide a **qa-pruebas**: "Escribe y ejecuta las pruebas de integración y e2e de $ARGUMENTS (flujo principal + flujos alternos: <lista>)." Si encuentra defectos, mándalos al subagente que corresponda y repite.

## 4. Revisar

Pide a **revisor-arquitectura**: "Revisa $ARGUMENTS. Archivos tocados: <lista>. Traza: <traza>." Si el veredicto es *CAMBIOS REQUERIDOS*, manda las acciones al subagente que corresponda y vuelve a pedir la revisión. Sin *APROBADO*, el CU no se cierra.

## 5. Cerrar

- Actualiza la fila de $ARGUMENTS en la tabla de avance de `docs/plan-implementacion.md`.
- Si aparecieron cambios al modelo, verifica que estén en `docs/pendientes-modelo.md`, y las decisiones nuevas en `docs/decisiones.md`.
- Responde al usuario con lo que quedó, las pruebas (cuántas y si pasan), los pendientes y el siguiente CU según el plan.
