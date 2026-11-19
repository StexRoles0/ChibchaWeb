---
name: verificar-capas
description: Verifica que el backend respeta la arquitectura por capas de ChibchaWEB (frontend → servicio → dominio ← persistencia) con import-linter y búsquedas de imports prohibidos.
when_to_use: Después de cambiar código en backend/chibchaweb, antes de entregar una tarea o cuando se sospeche que un servicio usa mapeadores u ORM.
allowed-tools: Bash(lint-imports:*), Grep, Read
---

# Verificar capas

1. Ejecuta `cd backend && lint-imports`.
2. Busca lo que el linter no ve (imports dentro de funciones, uso del ORM por atributo):

   - En `backend/chibchaweb/servicio/`: `persistencia|adaptadores|django|rest_framework|Mapeador|\.objects\.|importlib`
   - En `backend/chibchaweb/dominio/`: `django|rest_framework|psycopg|httpx|authlib|importlib` (solo `dominio/respaldo*` puede usar `cryptography`)
   - En `backend/chibchaweb/web/` y `backend/chibchaweb/tareas/`: `chibchaweb\.dominio|persistencia|adaptadores|Mapeador|\.objects\.`
   - En `backend/chibchaweb/persistencia/` y `backend/chibchaweb/adaptadores/`: `chibchaweb\.servicio|chibchaweb\.web`

3. Confirma que cada `class Mapeador\w+\(` de `persistencia/mapeadores.py` herede de `Mapeador[...]` **y** de su `Repositorio...`, y que los `__init__` de `servicio/servicios.py` solo reciban tipos `Repositorio*`, interfaces de integración, `GestorContingencia` o `UnidadDeTrabajo`.

Informa así:

```
lint-imports: N contratos OK / M rotos
Imports prohibidos: ninguno | archivo:línea → texto
Mapeadores sin repositorio: …
Servicios con dependencias concretas: …
```

Si algo falla, explica cómo arreglarlo con el patrón Repository: mover la interfaz al dominio e inyectar la implementación desde `config/contenedor.py`.
