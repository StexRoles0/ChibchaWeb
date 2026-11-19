---
name: revisar-conformidad
description: Compara todo el código del backend contra el modelo estructural (docs/modelo/*.md) y genera un reporte de clases, atributos y métodos faltantes, sobrantes o distintos.
when_to_use: Al cerrar una fase, antes de la entrega final o cuando el usuario pida verificar que el código coincide con el modelo de EA.
disable-model-invocation: true
context: fork
agent: revisor-arquitectura
---

# Conformidad del código con el modelo

1. Extrae de `docs/modelo/dominio.md`, `servicio.md`, `persistencia.md` y `adaptadores.md` la lista de clases (`### \`Nombre\``) con sus atributos y métodos (columnas de las tablas).
2. Para cada clase, encuentra su definición en `backend/chibchaweb/` (`class Nombre`) y compara:
   - los atributos: `_nombre_snake` en `__init__` o con `@property`;
   - los métodos: `def nombre_snake(` con los mismos parámetros, en snake_case y en el mismo orden;
   - la herencia o realización (`hereda de` / `implementa` en el encabezado de la clase);
   - si es abstracta (`ABC` y `@abstractmethod`).
3. Toda clase o miembro público que **no** esté en el modelo tiene que aparecer en `docs/pendientes-modelo.md`. Si no aparece, es un hallazgo.
4. Escribe el reporte en `docs/reporte-conformidad.md`:

```
# Reporte de conformidad — <fecha>
Resumen: X/98 clases conformes · Y hallazgos
| Clase | Miembro | Modelo | Código | Tipo (falta/sobra/difiere) |
```

5. Al final, lista los cambios que hay que llevar a EA (lo que está en `pendientes-modelo.md` más lo nuevo que se encontró).
